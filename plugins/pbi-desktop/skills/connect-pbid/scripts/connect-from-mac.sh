#!/bin/bash
# connect-from-mac.sh
# Wrapper for running PowerShell scripts inside a Parallels Windows VM from macOS.
# Usage: ./connect-from-mac.sh <vm-name> <script.ps1> [args...]
#
# Examples:
#   ./connect-from-mac.sh Macdows connect-and-enumerate.ps1
#   ./connect-from-mac.sh Macdows query-dax.ps1 -Port 53706 -Query "EVALUATE 'Sales'"
#
# Prerequisites:
#   - Parallels Desktop with prlctl CLI installed
#   - Windows VM running with Power BI Desktop open
#   - Shared folders enabled (macOS ~ mapped to \\Mac\Home\ in VM)
#   - NuGet CLI available inside the VM

set -euo pipefail


#region Arguments

VM_NAME="${1:?Usage: $0 <vm-name> <script.ps1> [args...]}"
SCRIPT="${2:?Usage: $0 <vm-name> <script.ps1> [args...]}"
shift 2
EXTRA_ARGS="$*"
CMD_ARGS=""
for arg in "$@"; do
    CMD_ARGS="${CMD_ARGS} \"${arg//\"/\\\"}\""
done

#endregion


#region Validation

if ! command -v prlctl &>/dev/null; then
    echo "ERROR: prlctl not found. Install Parallels Desktop CLI tools." >&2
    exit 1
fi

VM_STATUS=$(prlctl list --all | grep "$VM_NAME" | awk '{print $2}')
if [ "$VM_STATUS" != "running" ]; then
    echo "ERROR: VM '$VM_NAME' is not running (status: $VM_STATUS)." >&2
    exit 1
fi

#endregion


#region Resolve Script Path

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/$SCRIPT"

if [ ! -f "$SCRIPT_PATH" ]; then
    echo "ERROR: Script not found: $SCRIPT_PATH" >&2
    exit 1
fi

# Convert macOS path to Parallels shared folder path
# ~/Desktop/Git/pbi-desktop/scripts/foo.ps1 -> \\Mac\Home\Desktop\Git\pbi-desktop\scripts\foo.ps1
HOME_RELATIVE="${SCRIPT_PATH#$HOME/}"
WIN_PATH="\\\\Mac\\Home\\${HOME_RELATIVE//\//\\}"

#endregion


#region Execute

echo "VM: $VM_NAME"
echo "Script: $SCRIPT_PATH"
echo "Win path: $WIN_PATH"
echo "Args: $EXTRA_ARGS"
echo ""

prlctl exec "$VM_NAME" cmd.exe /c "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"$WIN_PATH\"${CMD_ARGS}"

#endregion
