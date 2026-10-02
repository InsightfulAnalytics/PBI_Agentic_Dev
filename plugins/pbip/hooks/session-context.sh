#!/bin/bash
#
# SessionStart hook: print the Power BI skill routing table and Desktop rules
# (session-context.md, next to this script) so they enter the session's context.
#
# Toggle with `session_context: false` in config.yaml. Always exits 0: a missing
# file or config must never stop a session from starting.

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)" || exit 0
HOOK_CONFIG="$HOOK_DIR/config.yaml"

if [[ -f "$HOOK_CONFIG" ]] && grep -qE "^session_context:[[:space:]]*false" "$HOOK_CONFIG" 2>/dev/null; then
    exit 0
fi

cat "$HOOK_DIR/session-context.md" 2>/dev/null
exit 0
