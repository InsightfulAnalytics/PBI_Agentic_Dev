#!/usr/bin/env bash
# Install pbir on Linux by running the published Windows build under Wine.
#
# Downloads the win_amd64 wheel of pbir-cli from PyPI, checks it against PyPI's SHA-256,
# unpacks it unchanged, creates a private Wine prefix and installs the `pbir-wine`
# launcher as ~/.local/bin/pbir. Run it again to upgrade; pass a version to pin one.
#
#   install-linux.sh            latest release
#   install-linux.sh 0.9.33     that release
#
# Needs curl, jq, unzip and a Wine: the powerbi-linux runtime when that project is
# installed (it is found through ~/.local/share/powerbi-linux/active.json), else `wine`.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
home="${PBIR_WINE_HOME:-$HOME/.local/share/pbir-wine}"
bindir="${PBIR_BIN_DIR:-$HOME/.local/bin}"
version="${1:-}"
active="$HOME/.local/share/powerbi-linux/active.json"

for tool in curl jq unzip sha256sum; do
  command -v "$tool" >/dev/null || { echo "Needs $tool." >&2; exit 1; }
done
[ "$(uname -s)" = "Linux" ] || { echo "Linux only. Elsewhere: uv tool install pbir-cli." >&2; exit 1; }

runtime=""; desktop_prefix=""
if [ -f "$active" ]; then
  runtime="$(jq -r '.runtime // empty' "$active")"
  desktop_prefix="$(jq -r '.prefix // empty' "$active")"
fi
if [ -n "$runtime" ] && [ -x "$runtime/bin/wine" ]; then wine="$runtime/bin/wine"
elif command -v wine >/dev/null; then wine="$(command -v wine)"
else echo "No Wine found. Install powerbi-linux (preferred) or a system wine." >&2; exit 1
fi

# 1. The wheel, verified against PyPI's own digest.
url="https://pypi.org/pypi/pbir-cli/json"
[ -n "$version" ] && url="https://pypi.org/pypi/pbir-cli/$version/json"
meta="$(curl -fsSL "$url")"
version="$(jq -r '.info.version' <<<"$meta")"
wheel_url="$(jq -r '.urls[] | select(.filename | test("win_amd64")) | .url' <<<"$meta")"
wheel_sha="$(jq -r '.urls[] | select(.filename | test("win_amd64")) | .digests.sha256' <<<"$meta")"
[ -n "$wheel_url" ] || { echo "pbir-cli $version publishes no win_amd64 wheel." >&2; exit 1; }

mkdir -p "$home/wheels"
wheel="$home/wheels/pbir_cli-$version-win_amd64.whl"
if [ ! -f "$wheel" ] || [ "$(sha256sum "$wheel" | cut -d' ' -f1)" != "$wheel_sha" ]; then
  echo "Downloading pbir-cli $version (Windows build)..."
  curl -fsSL -o "$wheel.part" "$wheel_url"
  [ "$(sha256sum "$wheel.part" | cut -d' ' -f1)" = "$wheel_sha" ] ||
    { rm -f "$wheel.part"; echo "SHA-256 mismatch on the downloaded wheel." >&2; exit 1; }
  mv "$wheel.part" "$wheel"
fi

# 2. Unpack it unchanged, then point `current` at it.
dest="$home/$version"
if [ ! -f "$dest/pbir_binary_wheel/runtime/pbir-runtime.exe" ]; then
  tmp="$(mktemp -d "$home/unpack.XXXXXX")"
  unzip -q "$wheel" -d "$tmp"
  rm -rf "$dest"
  mv "$tmp/pbir_cli-$version.data/purelib" "$dest"
  rm -rf "$tmp"
fi
ln -sfn "$version" "$home/current"

# 3. A private prefix, so offline commands never touch Power BI Desktop's own.
export WINEPREFIX="$home/prefix" WINEDEBUG=-all WINEDLLOVERRIDES="mscoree,mshtml=;winemenubuilder.exe=d"
if [ ! -d "$WINEPREFIX/drive_c" ]; then
  echo "Creating the Wine prefix..."
  "$(dirname "$wine")/wineboot" -i >/dev/null 2>&1 || "$wine" wineboot -i >/dev/null 2>&1
fi

# 4. Mirror the extra drive letters of the powerbi-linux profile (a W: drive mapped to a
#    work folder, say), so a path prints the same in both prefixes.
if [ -n "$desktop_prefix" ] && [ -d "$desktop_prefix/dosdevices" ]; then
  for link in "$desktop_prefix"/dosdevices/?:; do
    letter="$(basename "$link")"
    case "$letter" in c: | z:) continue ;; esac
    [ -e "$WINEPREFIX/dosdevices/$letter" ] || ln -s "$(readlink "$link")" "$WINEPREFIX/dosdevices/$letter"
  done
fi

# 5. One pbir configuration for both prefixes (connections, profiles, caches).
user_dir() { find "$1/drive_c/users" -mindepth 1 -maxdepth 1 -type d ! -name Public | head -1; }
mkdir -p "$home/config"
for p in "$WINEPREFIX" "$desktop_prefix"; do
  [ -n "$p" ] && [ -d "$p/drive_c/users" ] || continue
  local_appdata="$(user_dir "$p")/AppData/Local"
  [ -d "$local_appdata" ] || continue
  target="$local_appdata/pbir-tools"
  if [ -L "$target" ]; then continue; fi
  if [ -d "$target" ]; then cp -an "$target/." "$home/config/" && rm -rf "$target"; fi
  ln -s "$home/config" "$target"
done

# 6. The launcher.
mkdir -p "$bindir"
install -m 755 "$here/pbir-wine" "$bindir/pbir"

echo "Installed: $("$bindir/pbir" --version | tr -d '\r') as $bindir/pbir (wine: $wine)"
case ":$PATH:" in *":$bindir:"*) ;; *) echo "Add $bindir to PATH." ;; esac
