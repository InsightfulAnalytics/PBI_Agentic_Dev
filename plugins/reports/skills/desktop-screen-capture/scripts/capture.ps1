<#
Screen capture for Windows. Full virtual desktop, or one window by title/process.
Written once so it stops being hand-authored inline every session.

powershell -NoProfile -ExecutionPolicy Bypass -File capture.ps1 [-Out x.png] [-Title s | -Process n]
                                                                [-List] [-NoActivate] [-Scale n]
                                                                [-Delay ms] [-SelfTest]
#>
[CmdletBinding()]
param(
    [string]$Out,
    [string]$Title,
    [string]$Process,
    [switch]$List,
    [switch]$NoActivate,
    [double]$Scale = 1,
    [int]$Delay = 0,
    [switch]$SelfTest
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing, System.Windows.Forms

Add-Type @'
using System;
using System.Text;
using System.Runtime.InteropServices;

public class Win {
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr h);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)]
    public static extern int GetWindowText(IntPtr h, StringBuilder s, int max);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);

    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);

    // DWM gives the true visible frame; GetWindowRect includes the invisible resize border
    // on Win10/11 and yields a capture with dead margins.
    [DllImport("dwmapi.dll")]
    public static extern int DwmGetWindowAttribute(IntPtr h, int attr, out RECT r, int size);

    public delegate bool EnumProc(IntPtr h, IntPtr p);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);

    [DllImport("shcore.dll")] public static extern int SetProcessDpiAwareness(int v);
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
}
'@

# --- DPI awareness. Must happen before ANY measurement, or coordinates are wrong on a
# --- scaled display and the capture comes out cropped/offset. shcore is Win8.1+; fall back.
try { [void][Win]::SetProcessDpiAwareness(2) } catch { try { [void][Win]::SetProcessDPIAware() } catch {} }

function Get-Windows {
    $found = New-Object System.Collections.ArrayList
    $cb = [Win+EnumProc]{
        param($h, $p)
        if ([Win]::IsWindowVisible($h)) {
            $len = [Win]::GetWindowTextLength($h)
            if ($len -gt 0) {
                $sb = New-Object System.Text.StringBuilder ($len + 1)
                [void][Win]::GetWindowText($h, $sb, $sb.Capacity)
                # NOT $pid - that is a read-only automatic variable in PowerShell
                $procId = 0; [void][Win]::GetWindowThreadProcessId($h, [ref]$procId)
                $r = New-Object Win+RECT
                if ([Win]::DwmGetWindowAttribute($h, 9, [ref]$r, 16) -ne 0) { [void][Win]::GetWindowRect($h, [ref]$r) }
                $w = $r.R - $r.L; $ht = $r.B - $r.T
                # skip 0-size and the 1x1 helper windows Electron/Chrome leave lying around
                if ($w -gt 40 -and $ht -gt 40) {
                    $pname = try { (Get-Process -Id $procId -ErrorAction Stop).ProcessName } catch { '?' }
                    [void]$found.Add([PSCustomObject]@{
                        Handle = $h; PID = $procId; Process = $pname; Title = $sb.ToString()
                        X = $r.L; Y = $r.T; W = $w; H = $ht; Minimised = [Win]::IsIconic($h)
                    })
                }
            }
        }
        return $true
    }
    [void][Win]::EnumWindows($cb, [IntPtr]::Zero)
    return $found
}

function Save-Region {
    param([int]$X, [int]$Y, [int]$W, [int]$H, [string]$Path, [double]$Div)
    if ($W -le 0 -or $H -le 0) { throw "Refusing to capture a $($W)x$($H) region." }
    $bmp = New-Object System.Drawing.Bitmap $W, $H
    try {
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        try { $g.CopyFromScreen($X, $Y, 0, 0, (New-Object System.Drawing.Size $W, $H)) }
        finally { $g.Dispose() }

        if ($Div -gt 1) {
            $nw = [int]($W / $Div); $nh = [int]($H / $Div)
            $small = New-Object System.Drawing.Bitmap $nw, $nh
            $g2 = [System.Drawing.Graphics]::FromImage($small)
            try {
                $g2.InterpolationMode = 'HighQualityBicubic'
                $g2.DrawImage($bmp, 0, 0, $nw, $nh)
            } finally { $g2.Dispose() }
            $bmp.Dispose(); $bmp = $small; $W = $nw; $H = $nh
        }

        $dir = Split-Path $Path -Parent
        if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
        $bmp.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    } finally { $bmp.Dispose() }
    return @{ Path = $Path; W = $W; H = $H }
}

# ---------------------------------------------------------------- self test
if ($SelfTest) {
    $tmp = Join-Path $env:TEMP "capture-selftest-$PID.png"
    $vs = [System.Windows.Forms.SystemInformation]::VirtualScreen
    try {
        $r = Save-Region -X $vs.X -Y $vs.Y -W $vs.Width -H $vs.Height -Path $tmp -Div 2
        $len = (Get-Item $tmp).Length
        $img = [System.Drawing.Image]::FromFile($tmp)
        $dims = "$($img.Width)x$($img.Height)"; $img.Dispose()
        $okSize = $len -gt 10240
        $okDims = $r.W -eq [int]($vs.Width / 2)
        if ($okSize -and $okDims) { "PASS  $dims, $([int]($len/1024)) KB (virtual screen $($vs.Width)x$($vs.Height))" }
        else { "FAIL  size=$len bytes okSize=$okSize okDims=$okDims dims=$dims" ; exit 1 }
    } finally { Remove-Item $tmp -Force -ErrorAction SilentlyContinue }
    exit 0
}

# ---------------------------------------------------------------- list
if ($List) {
    Get-Windows | Sort-Object Process, Title |
        Format-Table PID, Process, @{n='Bounds';e={"$($_.W)x$($_.H) @$($_.X),$($_.Y)"}}, Minimised, Title -AutoSize |
        Out-String -Width 200
    exit 0
}

if (-not $Out) { $Out = Join-Path (Get-Location) ("capture-" + (Get-Date -Format 'HHmmss') + ".png") }
if (-not [System.IO.Path]::IsPathRooted($Out)) { $Out = Join-Path (Get-Location) $Out }

# ---------------------------------------------------------------- window capture
if ($Title -or $Process) {
    $all = Get-Windows
    $match = if ($Title) { $all | Where-Object { $_.Title -like "*$Title*" } }
             else        { $all | Where-Object { $_.Process -ieq $Process } }

    if (-not $match) {
        Write-Error ("No visible window matched {0}. Run with -List to see candidates." -f `
            $(if ($Title) { "title '*$Title*'" } else { "process '$Process'" }))
        exit 1
    }
    # largest match wins - splash screens and tooltips are small
    $w = $match | Sort-Object { $_.W * $_.H } -Descending | Select-Object -First 1
    if (@($match).Count -gt 1) {
        Write-Host "note: $(@($match).Count) windows matched; took the largest -> [$($w.Process)] $($w.Title)"
    }

    if ($w.Minimised) {
        if ($NoActivate) { Write-Error "Window '$($w.Title)' is minimised and -NoActivate was set. Cannot capture."; exit 1 }
        [void][Win]::ShowWindow($w.Handle, 9)   # SW_RESTORE
        Start-Sleep -Milliseconds 250
    }

    if (-not $NoActivate) {
        [void][Win]::SetForegroundWindow($w.Handle)
        # wait for it to actually come forward rather than sleeping a guessed interval
        $deadline = (Get-Date).AddMilliseconds(2000)
        while ((Get-Date) -lt $deadline -and [Win]::GetForegroundWindow() -ne $w.Handle) { Start-Sleep -Milliseconds 40 }
        if ([Win]::GetForegroundWindow() -ne $w.Handle) {
            Write-Host "warn: could not bring '$($w.Title)' to the front; capture may show what is over it."
        }
    }
    if ($Delay -gt 0) { Start-Sleep -Milliseconds $Delay }

    # re-read bounds: restoring or activating can move/resize the window
    $r = New-Object Win+RECT
    if ([Win]::DwmGetWindowAttribute($w.Handle, 9, [ref]$r, 16) -ne 0) { [void][Win]::GetWindowRect($w.Handle, [ref]$r) }
    $res = Save-Region -X $r.L -Y $r.T -W ($r.R - $r.L) -H ($r.B - $r.T) -Path $Out -Div $Scale
    "$($res.Path)"
    Write-Host "captured [$($w.Process)] $($w.Title) -> $($res.W)x$($res.H)"
    exit 0
}

# ---------------------------------------------------------------- full virtual desktop
if ($Delay -gt 0) { Start-Sleep -Milliseconds $Delay }
$vs = [System.Windows.Forms.SystemInformation]::VirtualScreen
$res = Save-Region -X $vs.X -Y $vs.Y -W $vs.Width -H $vs.Height -Path $Out -Div $Scale
"$($res.Path)"
Write-Host "captured virtual desktop $($vs.Width)x$($vs.Height) @$($vs.X),$($vs.Y) -> $($res.W)x$($res.H)"
