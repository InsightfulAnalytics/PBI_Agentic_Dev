#!/usr/bin/env bash
# Run Tabular Editor's `te` CLI against the model open in Power BI Desktop on Linux (Desktop under
# Wine, powerbi-linux).
#
# The Linux build of `te` cannot connect to Desktop: Desktop's Analysis Services takes Windows
# sign-in only. The Windows build runs under Wine in Desktop's own prefix and connects. This script
# fetches that build once from Tabular Editor's public CDN, finds Desktop's port and database and
# passes them as -s/-d, so no `te connect` state is needed between calls. Everything else goes to
# `te` as written, after an absolute Linux path is rewritten to Z:\....
#
#   te-desktop.sh query -q 'EVALUATE ROW("Rows", COUNTROWS(Sales))'
#   te-desktop.sh ls
#   te-desktop.sh add "Sales/Margin" -t Measure -p 'Expression=[Revenue] - [Cost]' --save
#   te-desktop.sh --update        fetch the latest Windows build, then exit
#
# Never run a data refresh (`refresh --execute`) against the model Desktop has open: the visuals are
# not told. For files on disk (TMDL) use the Linux build of `te` with -m instead.
set -euo pipefail

active="$HOME/.local/share/powerbi-linux/active.json"
home="${TE_WINE_HOME:-$HOME/.local/share/te-wine}"
url="https://cdn.tabulareditor.com/files/latest/cli/te-win-x64.zip"

[ -f "$active" ] || { echo "powerbi-linux is not installed (no $active)." >&2; exit 2; }
runtime="$(jq -r .runtime "$active")"; prefix="$(jq -r .prefix "$active")"
# A Wine process in Desktop's prefix while Desktop is closed lingers and blocks the next open.
systemctl --user is-active --quiet pbi-linux-session.service ||
  { echo "Power BI Desktop is not running. Open the project with: pbi-linux open <file.pbip>" >&2; exit 2; }
export WINEPREFIX="$prefix" WINEDEBUG=-all

# The Windows build, unpacked unchanged under ~/.local/share/te-wine/<version>. The CDN publishes no
# checksum, so the download is trusted as served over HTTPS.
fetch() {
  local tmp version
  mkdir -p "$home"
  tmp="$(mktemp -d "$home/fetch.XXXXXX")"
  curl -fsSL -o "$tmp/te.zip" "$url"
  unzip -q -o "$tmp/te.zip" te.exe -d "$tmp"
  version="$("$runtime/bin/wine" "$tmp/te.exe" --version 2>/dev/null | tr -d '\r' | tail -1)"
  [[ "$version" =~ ^[0-9][0-9.]*$ ]] || { rm -rf "$tmp"; echo "The downloaded te.exe did not run." >&2; exit 2; }
  mkdir -p "$home/$version"
  mv "$tmp/te.exe" "$home/$version/te.exe"
  rm -rf "$tmp"
  ln -sfn "$version" "$home/current"
  echo "te $version (Windows build) in $home/$version" >&2
}
if [ "${1:-}" = "--update" ]; then fetch; exit 0; fi
[ -f "$home/current/te.exe" ] || fetch

# Desktop writes its port (UTF-16) into the newest Analysis Services workspace; the model's
# database folder beside it is named <database>.<n>.db.
port_file="$(ls -t "$prefix"/drive_c/users/*/AppData/Local/Microsoft/Power\ BI\ Desktop/AnalysisServicesWorkspaces/*/Data/msmdsrv.port.txt 2>/dev/null | head -1)"
[ -n "$port_file" ] || { echo "No Analysis Services workspace yet: the model is still loading." >&2; exit 2; }
port="$(tr -d '\0\r\n\377\376' <"$port_file" | tr -cd '0-9')"
database="$(find "$(dirname "$port_file")" -maxdepth 1 -type d -name '*.db' -printf '%f\n' |
  sed -n 's/^\([0-9a-f-]\{36\}\)\.[0-9]*\.db$/\1/p' | head -1)"
[ -n "$database" ] || { echo "No model database in $(dirname "$port_file") yet." >&2; exit 2; }

# An absolute Linux path becomes Z:\... up to its longest existing prefix (as in pbir-wine).
to_windows() {
  local arg="$1" head tail=""
  case "$arg" in /?*) ;; *) printf '%s' "$arg"; return ;; esac
  head="$arg"
  while [ "$head" != "/" ] && [ ! -e "$head" ]; do
    tail="/${head##*/}$tail"
    head="${head%/*}"
    [ -z "$head" ] && head="/"
  done
  if [ "$head" = "/" ]; then printf '%s' "$arg"; return; fi
  printf 'Z:%s%s' "${head//\//\\}" "$tail"
}

# Add -s/-d for commands that work on a model, unless the caller named one. The subcommand is the
# first word that is neither an option nor the value of a global option.
sub=""; named=0; skip=0
for a in "$@"; do
  case "$a" in
    -s | --server | -d | --database | -m | --model | --local | --recent) named=1 ;;
  esac
  [ -n "$sub" ] && continue
  if [ "$skip" = 1 ]; then skip=0; continue; fi
  case "$a" in
    -s | --server | -d | --database | -m | --model | --output-format | --error-format | --auth) skip=1 ;;
    -*) ;;
    *) sub="$a" ;;
  esac
done
target=()
case "$sub" in
  query | list | ls | get | set | add | remove | rm | move | mv | rename | find | deps | bpa | validate | \
    vertipaq | script | macro | test | refresh | deploy | save-as | save | schemacheck)
    [ "$named" = 1 ] || target=(-s "localhost:$port" -d "$database") ;;
esac

args=()
for a in "$@"; do args+=("$(to_windows "$a")"); done
# Never wait on a prompt; `te --version` and `te --help` take no other option.
quiet=(); [ -n "$sub" ] && quiet=(--non-interactive)

"$runtime/bin/wine" "$home/current/te.exe" "${target[@]}" "${quiet[@]}" "${args[@]}" | tr -d '\r'
