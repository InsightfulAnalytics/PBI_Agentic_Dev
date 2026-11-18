#!/usr/bin/env bash
# Query the model open in Power BI Desktop on Linux (Desktop under Wine, powerbi-linux).
#
# The Linux stand-in for `pbir model -q` and query-dax.ps1: it runs a small ADOMD client
# inside Desktop's own Wine prefix, where Desktop's Analysis Services port and its ADOMD
# assembly both live. Prints JSON: {"columns": [...], "rows": [[...]], "rowCount": n}, or
# {"error": "..."} with exit 1.
#
#   pbid-dax.sh 'EVALUATE ROW("Rows", COUNTROWS(Sales))'
#   pbid-dax.sh -f query.dax
#   pbid-dax.sh --port          print the Analysis Services port and exit
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
active="$HOME/.local/share/powerbi-linux/active.json"
cache="${XDG_CACHE_HOME:-$HOME/.cache}/pbid-linux"

[ -f "$active" ] || { echo "powerbi-linux is not installed (no $active)." >&2; exit 2; }
runtime="$(jq -r .runtime "$active")"; prefix="$(jq -r .prefix "$active")"
systemctl --user is-active --quiet pbi-linux-session.service ||
  { echo "Power BI Desktop is not running. Open the project with: pbi-linux open <file.pbip>" >&2; exit 2; }

# Desktop writes its port (UTF-16) into the newest Analysis Services workspace.
port_file="$(ls -t "$prefix"/drive_c/users/*/AppData/Local/Microsoft/Power\ BI\ Desktop/AnalysisServicesWorkspaces/*/Data/msmdsrv.port.txt 2>/dev/null | head -1)"
[ -n "$port_file" ] || { echo "No Analysis Services workspace yet: the model is still loading." >&2; exit 2; }
port="$(tr -d '\0\r\n\377\376' <"$port_file" | tr -cd '0-9')"

if [ "${1:-}" = "--port" ]; then echo "$port"; exit 0; fi

mkdir -p "$cache"
work="$(mktemp -d "$cache/run.XXXXXX")"; trap 'rm -rf "$work"' EXIT
if [ "${1:-}" = "-f" ]; then cp "$2" "$work/query.dax"; else printf '%s' "${1:?a DAX query, or -f FILE}" >"$work/query.dax"; fi

export WINEPREFIX="$prefix" WINEDEBUG=-all
win() { printf 'Z:%s' "${1//\//\\}"; }

exe="$cache/pbid-dax.exe"
if [ ! -f "$exe" ] || [ "$here/pbid-dax.cs" -nt "$exe" ]; then
  "$runtime/bin/wine" 'C:\windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe' /nologo \
    "/out:$(win "$exe")" "$(win "$here/pbid-dax.cs")" >"$work/csc.log" 2>&1 ||
    { cat "$work/csc.log" >&2; exit 2; }
fi

code=0
"$runtime/bin/wine" "$exe" "$port" "$(win "$work/query.dax")" "$(win "$work/out.json")" >/dev/null 2>&1 || code=$?
[ -f "$work/out.json" ] || { echo '{"error":"the query client wrote no result"}'; exit 2; }
cat "$work/out.json"
exit "$code"
