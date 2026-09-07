# Finding an ADOMD.NET or TOM Assembly, and Matching It to the Host

Two steps, in this order. **Probe for an assembly that is already installed. Then check its target
framework against the host that will load it.** Doing the second step after the exception costs a
wasted diagnosis, because the exception names types rather than frameworks.

## Probe first, install second

Section 1 of SKILL.md installs `Microsoft.AnalysisServices.retail.amd64` and
`Microsoft.AnalysisServices.AdomdClient.retail.amd64` into `$env:TEMP\tom_nuget\...\lib\net45\`. That
path only exists once something has created it, and a Windows machine that runs Power BI tooling has
usually shipped these assemblies already, without a NuGet CLI anywhere on it. Probe before
installing:

```powershell
# ADOMD.NET (DAX queries) and TOM (model metadata), wherever a tool has shipped them
Get-ChildItem $env:ProgramFiles -Recurse -ErrorAction SilentlyContinue `
    -Include 'Microsoft.AnalysisServices.AdomdClient.dll',
             'Microsoft.AnalysisServices.Tabular.dll' |
    Select-Object FullName, @{n='Version'; e={$_.VersionInfo.FileVersion}}
```

Run the same probe over `${env:ProgramFiles(x86)}` and, for per-user installs,
`$env:LOCALAPPDATA\Programs`. If it finds nothing usable, fall back to the `nuget install` block in
SKILL.md section 1.

## Which tools ship a copy, and what to check

Treat this as a probe list, not an inventory. Which of these exist is a property of the machine, so
verify the hit and its target framework before loading it.

| A machine with this installed | has a build at | Check before loading |
|---|---|---|
| DAX Studio | `<Program Files>\DAX Studio\bin\` | Ships ADOMD.NET **and** the TOM assemblies (`Microsoft.AnalysisServices.Core.dll`, `.Tabular.dll`) side by side. A .NET Framework build, so it needs no NuGet step under Windows PowerShell 5.1 |
| Tabular Editor 3 | the TE3 install root | A .NET 8 build. `Add-Type` under Windows PowerShell 5.1 throws (see below) |
| SQLBI Bravo | its install root | Ships ADOMD.NET. Framework varies by release; check it |
| Measure Killer | its `_internal` folder | Ships ADOMD.NET. Framework varies by release; check it |
| The `.retail.amd64` NuGet packages | `<pkgDir>\<package>\lib\net45\` | `net45`, so Windows PowerShell 5.1 loads it |
| The unified `Microsoft.AnalysisServices` / `Microsoft.AnalysisServices.AdomdClient` packages | `<pkgDir>\<package>\lib\<tfm>\` | Ships `net472`, `net6.0` and `net8.0`. Pick the folder that matches the host |

Read the target framework off a candidate rather than guessing it. The attribute is stored as a plain
UTF-8 string in the assembly's metadata, so a byte read answers it on every build, with nothing loaded
and nothing to throw. First match wins:

```powershell
$dll  = '<full path from the probe>'
$text = [Text.Encoding]::UTF8.GetString([IO.File]::ReadAllBytes($dll))
[regex]::Match($text, '\.NET(Framework|CoreApp|Standard),Version=v[\d.]+').Value
```

| What comes back | Verdict |
|---|---|
| `.NETFramework,Version=v4.5` (any `.NETFramework,`) | A .NET Framework build. `Add-Type` under Windows PowerShell 5.1 loads it |
| `.NETCoreApp,Version=v8.0` | A .NET 8 build. Needs `pwsh` 7 or a `net8.0` project |
| `.NETCoreApp,Version=v3.0`, or any other `.NETCoreApp,` | An older .NET Core build. It throws the same `ReflectionTypeLoadException` under 5.1 that the .NET 8 case does |
| `.NETStandard,Version=v2.0` | A portable build. It can load under 5.1 where the netstandard facades resolve, so settle this one with the load test rather than the table |
| An empty string | The attribute is absent from the file. Go to the load test |

The string says what the build targets. Whether *this* host can load it is a second question, and
`Add-Type` answers that one directly. Ask it in a throwaway process:

```powershell
& powershell.exe -NoProfile -Command "try { Add-Type -Path '$dll' -ErrorAction Stop; 'LOADED' } catch { 'THREW: ' + `$_.Exception.GetBaseException().GetType().Name }"
```

`LOADED` means load it in the real session. `THREW: ReflectionTypeLoadException` means the host is
wrong for the assembly and the next section applies. Keep it to one candidate per process: two
assemblies that share an identity cannot both be loaded into one appdomain, so a second `Add-Type`
reports success while the session goes on using the first, and the reflection-only route refuses
outright with `API restriction: The assembly ... has already loaded from a different location`.

Three probes that look like they answer this and do not:

- `[Reflection.AssemblyName]::GetAssemblyName($dll)` returns the assembly's own version and never the
  target framework.
- `ImageRuntimeVersion` reads `v4.0.30319` on a .NET Framework build and a .NET 8 build alike.
- `ReflectionOnlyLoadFrom($dll).GetCustomAttributesData()` fails on exactly the builds worth
  triaging. Reading the attribute has to resolve `System.Runtime`, which a reflection-only context
  will not do, so instead of a value it throws `Cannot resolve dependency to assembly 'System.Runtime,
  Version=8.0.0.0' ... because it has not been preloaded`. That message does name the framework, so it
  can be read as a verdict from inside a `catch`, but it buys with an exception path what the byte
  read above states plainly.

The `lib\<tfm>\` folder name in a NuGet layout answers the same question with no code at all, so
prefer it whenever the candidate came out of a package rather than a tool's install folder.

## Matching the framework to the host

| Assembly target | Loads under | Does not load under |
|---|---|---|
| `net45`, `net472` | Windows PowerShell 5.1 (`powershell.exe`), and .NET Framework apps | .NET 6/8 hosts |
| `net6.0`, `net8.0` | PowerShell 7 (`pwsh`), and a `net8.0` project | Windows PowerShell 5.1 |

Windows PowerShell 5.1 runs on the .NET Framework CLR and cannot load a .NET 8 assembly. Pointing
`Add-Type -Path` at one throws:

```
ReflectionTypeLoadException: Unable to load one or more of the requested types
```

The message names types, not frameworks, so it reads like a corrupt or partial install. It is not:
the assembly is fine and the host is wrong. Three ways through, in order of cost:

1. **Load a .NET Framework build instead.** The `.retail.amd64` NuGet packages install `lib\net45\`
   assemblies, and a machine with DAX Studio has a .NET Framework build in its `bin` folder. Either
   loads cleanly under PowerShell 5.1. This is the right answer for everything in this skill's
   PowerShell path.
2. **Switch host to PowerShell 7 (`pwsh`).** The unified `Microsoft.AnalysisServices` and
   `Microsoft.AnalysisServices.AdomdClient` packages ship `net472`, `net6.0` and `net8.0`, so `pwsh`
   can load the modern build. The separate `Microsoft.AnalysisServices.NetCore.retail.amd64` package
   is a different, stale package name pinned at `netcoreapp3.0`; prefer the unified name. (Package
   19.114.12, checked on nuget.org 2026-09-07.)
   Retest: `nuget list Microsoft.AnalysisServices` and read the `lib\` folder names of the download.
3. **Do the work from a `net8.0` project rather than PowerShell.** This skill already ships one:
   `scripts/daxlib-tom/daxlib-tom.csproj` targets `net8.0` and references `Microsoft.AnalysisServices`.
   Use it as the template for anything needing current TOM features, which is why
   [daxlib.md](./daxlib.md) lists a .NET 8 SDK as a prerequisite.

A compatibility-level error or a missing TOM type means the `.retail.amd64` package is too old and
the newer package is wanted. That upgrade is a *host* change as much as a package change: take route
2 or 3, never `Add-Type` under 5.1.

## On Linux and macOS

The `net6.0`/`net8.0` assemblies load fine on both, so TOM and ADOMD.NET are available. What is not
available is a local engine: `msmdsrv.exe` ships with Power BI Desktop, so there is no
`localhost:<port>` to connect to and nothing in SKILL.md's port-discovery section applies. Route
instead to:

- **A published model over XMLA**, `powerbi://api.powerbi.com/v1.0/myorg/<Workspace>`, authenticating
  with an access token rather than integrated security. `fab` or `az` mints the token (fabric-cli
  `references/querying-data.md`).
- **The `te` CLI** (`tabular-editor:te-cli`), which is cross-platform and speaks both XMLA and a local
  model folder with `-m`.
- **Offline TMDL validation** with `plugins/pbip/hooks/bin/tmdl-validate-<platform>` when the question
  is only whether the model parses.

On macOS with Power BI Desktop inside a VM, the Windows path in this file applies inside the VM; see
[parallels-macos.md](./parallels-macos.md).
