#!/usr/bin/env bash
#
# Bootstrap an agent environment for Power BI work: resolve a writable clone of this
# marketplace, register it with Claude Code, install the toolchain that exists on this
# platform, and print a capability report naming what does NOT exist here.
#
# The capability report is the point. An agent that learns on turn one that Power BI Desktop
# and the pbir CLI do not exist on Linux stops planning around them; an agent that finds out
# by failing burns several turns first.
#
# Usage:
#   bash scripts/bootstrap-agent-env.sh              # full setup, idempotent
#   bash scripts/bootstrap-agent-env.sh --refresh    # update marketplace and plugins only
#   bash scripts/bootstrap-agent-env.sh --check      # print the capability report, change nothing
#   bash scripts/bootstrap-agent-env.sh --no-tools   # skip toolchain installs
#   bash scripts/bootstrap-agent-env.sh --uninstall  # remove what this script added to shell rc
#
set -uo pipefail

REPO_URL="https://github.com/InsightfulAnalytics/PBI_Agentic_Dev.git"
MARKETPLACE="power-bi-agentic-dev"
SENTINEL_OPEN="# >>> pbi-agentic-dev >>>"
SENTINEL_CLOSE="# <<< pbi-agentic-dev <<<"

MODE="full"
for a in "$@"; do
  case "$a" in
    --refresh)   MODE="refresh" ;;
    --check)     MODE="check" ;;
    --no-tools)  MODE="no-tools" ;;
    --uninstall) MODE="uninstall" ;;
    -h|--help)   sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) printf 'unknown argument: %s\n' "$a" >&2; exit 2 ;;
  esac
done

say()  { printf '%s\n' "$*"; }
warn() { printf 'warning: %s\n' "$*" >&2; }
have() { command -v "$1" >/dev/null 2>&1; }

case "$(uname -s 2>/dev/null || echo unknown)" in
  Linux*)   PLATFORM="linux" ;;
  Darwin*)  PLATFORM="macos" ;;
  MINGW*|MSYS*|CYGWIN*) PLATFORM="windows" ;;
  *)        PLATFORM="unknown" ;;
esac
ARCH="$(uname -m 2>/dev/null || echo unknown)"

# --- resolve the clone ----------------------------------------------------------------
is_marketplace() {
  [ -f "$1/.claude-plugin/marketplace.json" ] &&
    grep -q "\"$MARKETPLACE\"" "$1/.claude-plugin/marketplace.json" 2>/dev/null
}

resolve_root() {
  if [ -n "${PBI_MARKETPLACE_ROOT:-}" ] && is_marketplace "$PBI_MARKETPLACE_ROOT"; then
    printf '%s' "$PBI_MARKETPLACE_ROOT"; return 0
  fi
  local d; d="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)"
  while [ -n "$d" ] && [ "$d" != "/" ]; do
    if is_marketplace "$d"; then printf '%s' "$d"; return 0; fi
    local p; p="$(dirname "$d")"; [ "$p" = "$d" ] && break; d="$p"
  done
  return 1
}

if [ "$MODE" = "uninstall" ]; then
  for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
    [ -f "$rc" ] || continue
    if grep -qF "$SENTINEL_OPEN" "$rc"; then
      tmp="$(mktemp)"
      sed "/$(printf '%s' "$SENTINEL_OPEN" | sed 's/[][\\/.*^$]/\\&/g')/,/$(printf '%s' "$SENTINEL_CLOSE" | sed 's/[][\\/.*^$]/\\&/g')/d" "$rc" > "$tmp"
      mv "$tmp" "$rc"; say "removed the pbi-agentic-dev block from $rc"
    fi
  done
  say "shell rc cleaned. The clone and any installed plugins were left alone."
  exit 0
fi

ROOT="$(resolve_root || true)"
if [ -z "$ROOT" ] && [ "$MODE" != "check" ]; then
  ROOT="${PBI_MARKETPLACE_ROOT:-$HOME/.pbi-agentic-dev}"
  if [ ! -d "$ROOT/.git" ]; then
    say "cloning $MARKETPLACE into $ROOT"
    git clone --depth 1 "$REPO_URL" "$ROOT" || { warn "clone failed"; exit 1; }
  fi
fi
[ -n "$ROOT" ] || { warn "no marketplace clone found and --check cannot create one"; exit 1; }
export PBI_MARKETPLACE_ROOT="$ROOT"

# --- persist PBI_MARKETPLACE_ROOT ------------------------------------------------------
persist_env() {
  local rc="$HOME/.bashrc"
  [ -f "$rc" ] || touch "$rc"
  grep -qF "$SENTINEL_OPEN" "$rc" && return 0
  {
    printf '%s\n' "$SENTINEL_OPEN"
    printf 'export PBI_MARKETPLACE_ROOT=%q\n' "$ROOT"
    printf 'export PYTHONIOENCODING=utf-8\n'
    printf 'export PYTHONUTF8=1\n'
    printf 'case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac\n'
    printf '%s\n' "$SENTINEL_CLOSE"
  } >> "$rc"
  say "persisted PBI_MARKETPLACE_ROOT to $rc"
}

# --- register the marketplace ----------------------------------------------------------
register() {
  have claude || { warn "claude CLI not found; install with: npm install -g @anthropic-ai/claude-code"; return 1; }
  # A local path registers a `directory` source, which attaches live from the folder: no
  # per-commit cache, no version bump, no `plugin update` needed to pick an edit up.
  if [ "$MODE" = "refresh" ]; then
    claude plugin marketplace update "$MARKETPLACE" >/dev/null 2>&1 || true
  else
    claude plugin marketplace add "$ROOT" >/dev/null 2>&1 || true
  fi
  local names
  names="$(python - "$ROOT/.claude-plugin/marketplace.json" <<'PY' 2>/dev/null
import json, sys
with open(sys.argv[1], encoding="utf-8") as fh:
    print("\n".join(p["name"] for p in json.load(fh).get("plugins", [])))
PY
)"
  [ -n "$names" ] || { warn "could not read plugin names from marketplace.json"; return 1; }
  local n
  for n in $names; do
    if [ "$MODE" = "refresh" ]; then
      claude plugin update "$n@$MARKETPLACE" >/dev/null 2>&1 || true
    else
      claude plugin install "$n@$MARKETPLACE" >/dev/null 2>&1 || true
    fi
  done
  say "registered $MARKETPLACE and its $(printf '%s' "$names" | wc -w | tr -d ' ') plugins"
}

# --- toolchain -------------------------------------------------------------------------
install_tools() {
  mkdir -p "$HOME/.local/bin"
  case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) PATH="$HOME/.local/bin:$PATH" ;; esac

  if ! have uv; then
    say "installing uv"
    curl -fsSL https://astral.sh/uv/install.sh | sh >/dev/null 2>&1 || warn "uv install failed"
  fi
  if ! have fab; then
    say "installing the Fabric CLI (fab)"
    if have uv; then uv tool install ms-fabric-cli >/dev/null 2>&1 || warn "fab install failed"
    else python -m pip install --user ms-fabric-cli >/dev/null 2>&1 || warn "fab install failed"; fi
  fi
  if ! have te && [ "$PLATFORM" != "windows" ]; then
    # Recipe lives in plugins/tabular-editor/skills/te-cli/references/get-te-cli.md
    local os arch
    [ "$PLATFORM" = "macos" ] && os="osx" || os="linux"
    case "$ARCH" in aarch64|arm64) arch="arm64" ;; *) arch="x64" ;; esac
    say "installing the Tabular Editor CLI (te-$os-$arch)"
    curl -fsSL "https://cdn.tabulareditor.com/files/cli/latest/te-$os-$arch.tar.gz" \
      | tar -xz -C "$HOME/.local/bin" te 2>/dev/null && chmod +x "$HOME/.local/bin/te" \
      || warn "te install failed"
  fi
  # jq is a hard dependency of plugins/pbip/hooks/validate-pbir.sh. Without it that hook
  # silently exits 0 on a broken file, which reads as "valid".
  if ! have jq; then
    say "installing jq"
    if   have apt-get; then sudo apt-get install -y -qq jq >/dev/null 2>&1 || warn "jq install failed"
    elif have dnf;     then sudo dnf install -y -q jq     >/dev/null 2>&1 || warn "jq install failed"
    elif have brew;    then brew install jq               >/dev/null 2>&1 || warn "jq install failed"
    else warn "no package manager found for jq"; fi
  fi
  if ! python -c "import fitz" >/dev/null 2>&1; then
    say "installing pymupdf (renders an ExportTo PDF to PNG; no system dependency)"
    python -m pip install --user --quiet pymupdf >/dev/null 2>&1 || warn "pymupdf install failed"
  fi
  # pbir is deliberately NOT attempted. See the capability report.
}

# --- capability report -------------------------------------------------------------------
report() {
  local tv="$ROOT/plugins/pbip/hooks/bin/tmdl-validate-${PLATFORM/macos/darwin}-${ARCH/x86_64/x64}"
  [ "$PLATFORM" = "windows" ] && tv="$tv.exe"

  local avail=""
  for t in fab te az python node jq claude git gh; do have "$t" && avail="$avail $t"; done
  python -c "import fitz" >/dev/null 2>&1 && avail="$avail pymupdf"
  [ -x "$tv" ] && avail="$avail tmdl-validate"

  cat <<EOF

================ Power BI agent capability report ================
platform    : ${PLATFORM}-${ARCH}
marketplace : ${ROOT}
              (directory source: skills attach live from this folder, no cache, no version bump)

AVAILABLE  :${avail:- none}

EOF

  if [ "$PLATFORM" != "windows" ]; then
    cat <<'EOF'
UNAVAILABLE on this platform. Do not plan around them:

  pbir CLI          Every pbir-cli release publishes exactly two wheels, macosx_11_0_arm64 and
                    win_amd64, and no sdist. On Linux `pip install pbir-cli` and
                    `uv tool install pbir-cli` both fail with "No matching distribution found".
                    This is absence, not a degraded mode: do not spend turns on the install.
                    Instead: hand-author PBIR JSON from the pbip:pbir-format skill's
                    examples/visuals/ templates, and publish with `fab import`
                    (byConnection reports only).

  Power BI Desktop  No Linux build, so `pbir desktop`, the reports:pbi-verify-loop skill and the
                    whole pbi-desktop:connect-pbid skill are inert here.
                    Instead, to SEE a report: render server-side with the ExportTo API
                    (POST groups/{ws}/reports/{id}/ExportTo, poll, GET the file), then convert
                    the PDF to PNG with pymupdf. See fabric-cli references/reports.md.
                    Note `fab api` corrupts binary bodies, so fetch the file over raw HTTP with
                    an `az account get-access-token` bearer token.

  Windows PowerShell 5.1, DAX Studio, Tabular Editor 2/3, a local msmdsrv instance.
                    ADOMD/TOM against a LOCAL model is therefore impossible. Against a PUBLISHED
                    model, use `te` or XMLA with token auth.
EOF
  fi

  cat <<EOF

VALIDATION available offline here:
  TMDL   ${tv}
         Runs standalone on a file or folder path: "tmdl-validate <path>". Bundled with the
         plugin, no install.
  PBIR   ${ROOT}/plugins/pbip/hooks/validate-pbir.sh
         This is a PostToolUse HOOK, not a CLI: it reads a JSON tool-use payload on stdin and
         needs jq. Without jq it exits 0 on a broken file, which reads as "valid". It is not a
         general PBIR validator, so treat a clean run as weak evidence.

LEARNINGS : PBI_MARKETPLACE_ROOT is set and the clone is writable, so a new learning goes in the
            skill that owns it. Read ${ROOT}/LEARNINGS.md, then use
            bash "\$PBI_MARKETPLACE_ROOT/scripts/record-learning.sh".
==================================================================
EOF
}

case "$MODE" in
  check)   report ;;
  refresh) register; report ;;
  no-tools) persist_env; register; report ;;
  full)    persist_env; register; install_tools; report ;;
esac

if [ "$MODE" != "check" ]; then
  mkdir -p "$ROOT" && report > "$ROOT/.bootstrap-report.txt" 2>/dev/null || true
fi
exit 0
