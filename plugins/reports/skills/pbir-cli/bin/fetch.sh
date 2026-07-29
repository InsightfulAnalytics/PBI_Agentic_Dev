#!/usr/bin/env bash
# Download the portable pbir binaries for this platform into this folder.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

REPO="maxanatsko/pbir.tools"
VERSION="${1:-latest}"

if ! command -v gh >/dev/null; then
  echo "Needs the GitHub CLI. Install it, run 'gh auth login', then try again." >&2
  exit 1
fi

case "$(uname -s)" in
  Darwin) pattern="pbir-portable-macos-arm64.tar.gz" ;;
  MINGW* | MSYS* | CYGWIN*) pattern="pbir-portable-windows-x64.exe" ;;
  *)
    echo "No portable build is published for $(uname -s). Use 'uv tool install pbir-cli' instead." >&2
    exit 1
    ;;
esac

if [ "${VERSION}" = "latest" ]; then
  gh release download --repo "${REPO}" --pattern "${pattern}" --clobber
else
  gh release download "${VERSION}" --repo "${REPO}" --pattern "${pattern}" --clobber
fi

echo "Downloaded ${pattern}. See README.md for how to run it, and delete it whenever you want the space back."
