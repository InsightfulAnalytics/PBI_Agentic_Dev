#!/usr/bin/env bash
#
# Record a learning into the skill that owns it, on a branch, as a pull request.
#
# The plugin cache is not a git working copy, so "write it into the skill's references" is only
# actionable when a writable clone of this marketplace exists. This script resolves that clone,
# appends the note, runs the hygiene scan, and opens a PR. It never commits to main.
#
# Usage:
#   scripts/record-learning.sh --skill pbip/tmdl --title "Blank line after ///" \
#       --file references/authoring-gotchas.md --body-file note.md
#   scripts/record-learning.sh --skill reports/pbir-cli --title "..." --body "one liner"
#   scripts/record-learning.sh --scope machine-local --skill pbi-desktop/connect-pbid --title "..."
#
# Read LEARNINGS.md before choosing --scope. The boundary rule there is the whole point.
#
set -euo pipefail

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
note() { printf '%s\n' "$*" >&2; }

SKILL=""; TITLE=""; BODY=""; BODY_FILE=""; TARGET=""; SCOPE="portable"; DRY=0; NO_PR=0

while [ $# -gt 0 ]; do
  case "$1" in
    --skill)     SKILL="${2:-}"; shift 2 ;;
    --title)     TITLE="${2:-}"; shift 2 ;;
    --body)      BODY="${2:-}"; shift 2 ;;
    --body-file) BODY_FILE="${2:-}"; shift 2 ;;
    --file)      TARGET="${2:-}"; shift 2 ;;
    --scope)     SCOPE="${2:-}"; shift 2 ;;
    --dry-run)   DRY=1; shift ;;
    --no-pr)     NO_PR=1; shift ;;
    -h|--help)   sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)           die "unknown argument: $1" ;;
  esac
done

# --- machine-local short circuit ------------------------------------------------------
# A machine-local fact must never enter a public repo. Refuse, and name the right destination.
if [ "$SCOPE" = "machine-local" ]; then
  slug_skill="${SKILL##*/}"
  cat >&2 <<EOF
Refusing to write a machine-local note into the marketplace: this repository is public and the
note would mislead every other machine that installs the plugin.

Write it to the agent's own memory file instead:
  Claude Code   ~/.claude/rules/${slug_skill:-<skill>}.md
  Cursor        .cursor/rules/${slug_skill:-<skill>}.mdc
  Copilot       .github/instructions/${slug_skill:-<skill>}.instructions.md

Before you do, re-read the generalisation table in LEARNINGS.md. Most machine-local facts are the
residue of a search that succeeded once, and the search itself is portable. If the generalised form
survives, re-run this script without --scope machine-local.
EOF
  exit 3
fi

case "$SCOPE" in portable|scoped) ;; *) die "--scope must be portable, scoped or machine-local" ;; esac
[ -n "$SKILL" ]  || die "--skill <plugin>/<skill> is required"
[ -n "$TITLE" ]  || die "--title is required"

# --- resolve the writable clone -------------------------------------------------------
is_marketplace() {
  [ -f "$1/.claude-plugin/marketplace.json" ] &&
    grep -q '"power-bi-agentic-dev"' "$1/.claude-plugin/marketplace.json" 2>/dev/null
}

ROOT="${PBI_MARKETPLACE_ROOT:-}"
if [ -z "$ROOT" ]; then
  d="$(cd "$(dirname "$0")/.." && pwd)"
  while [ "$d" != "/" ] && [ -n "$d" ]; do
    if is_marketplace "$d"; then ROOT="$d"; break; fi
    parent="$(dirname "$d")"; [ "$parent" = "$d" ] && break; d="$parent"
  done
fi
[ -n "$ROOT" ] || die "no writable marketplace clone found. Set PBI_MARKETPLACE_ROOT, or run scripts/bootstrap-agent-env.sh"
is_marketplace "$ROOT" || die "PBI_MARKETPLACE_ROOT=$ROOT is not a power-bi-agentic-dev clone"
git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1 || die "$ROOT is not a git working copy, so a note written there would be discarded by the next plugin update"

SKILL_DIR="$ROOT/plugins/${SKILL%%/*}/skills/${SKILL##*/}"
[ -d "$SKILL_DIR" ] || die "no such skill: $SKILL (looked in $SKILL_DIR)"

# --- resolve the destination file -----------------------------------------------------
if [ -z "$TARGET" ]; then
  TARGET="references/learnings.md"
  note "no --file given, defaulting to $TARGET"
  note "prefer an existing references/*.md that already owns the topic: one fact, one place"
fi
DEST="$SKILL_DIR/$TARGET"
mkdir -p "$(dirname "$DEST")"

# --- assemble the note ----------------------------------------------------------------
if [ -n "$BODY_FILE" ]; then
  [ -f "$BODY_FILE" ] || die "--body-file not found: $BODY_FILE"
  BODY="$(cat "$BODY_FILE")"
fi
[ -n "$BODY" ] || die "one of --body or --body-file is required"

TODAY="$(date +%Y-%m-%d)"
SLUG="$(printf '%s' "$TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]\+/-/g; s/^-//; s/-$//' | cut -c1-50)"
BRANCH="learning/${SKILL##*/}/${TODAY}-${SLUG}"

TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
{
  [ -f "$DEST" ] && { cat "$DEST"; printf '\n'; } || printf '# Learnings\n\n'
  printf '## %s\n\n' "$TITLE"
  printf '%s\n' "$BODY"
  printf '\nVerified %s.\n' "$TODAY"
} > "$TMP"

if [ "$DRY" = "1" ]; then
  note "--- dry run, would append to $DEST on branch $BRANCH ---"
  diff -u "${DEST:-/dev/null}" "$TMP" 2>/dev/null || true
  exit 0
fi

# --- branch, write, check, commit -----------------------------------------------------
START_BRANCH="$(git -C "$ROOT" rev-parse --abbrev-ref HEAD)"
[ "$START_BRANCH" = "HEAD" ] && die "clone is in detached HEAD; check out a branch first"

git -C "$ROOT" checkout -q -b "$BRANCH" 2>/dev/null || git -C "$ROOT" checkout -q "$BRANCH"
cp "$TMP" "$DEST"
git -C "$ROOT" add -- "$DEST"

if ! python "$ROOT/scripts/check-skill-hygiene.py" --staged; then
  git -C "$ROOT" restore --staged -- "$DEST" 2>/dev/null || git -C "$ROOT" reset -q HEAD -- "$DEST"
  git -C "$ROOT" checkout -q -- "$DEST" 2>/dev/null || rm -f "$DEST"
  git -C "$ROOT" checkout -q "$START_BRANCH"
  git -C "$ROOT" branch -q -D "$BRANCH" 2>/dev/null || true
  die "hygiene scan failed; nothing was committed. Fix the note and retry."
fi

git -C "$ROOT" commit -q -m "docs(${SKILL##*/}): ${TITLE}" -m "Recorded via scripts/record-learning.sh. Scope: ${SCOPE}."
note "committed to $BRANCH"

# --- pull request ---------------------------------------------------------------------
if [ "$NO_PR" = "1" ]; then
  note "--no-pr given. Push and open a PR yourself: git -C \"$ROOT\" push -u origin $BRANCH"
  exit 0
fi
if ! command -v gh >/dev/null 2>&1; then
  note "gh not installed. The commit is on $BRANCH in $ROOT."
  note "Push it yourself: git -C \"$ROOT\" push -u origin $BRANCH"
  exit 0
fi
git -C "$ROOT" push -q -u origin "$BRANCH" || die "push failed; the commit is safe on $BRANCH"
gh --repo "$(git -C "$ROOT" remote get-url origin)" pr create \
  --head "$BRANCH" --title "docs(${SKILL##*/}): ${TITLE}" \
  --body "Recorded via \`scripts/record-learning.sh\`. Scope: ${SCOPE}. Lands in \`${SKILL}/${TARGET}\`." \
  || note "PR creation failed; the branch is pushed, open the PR by hand"
