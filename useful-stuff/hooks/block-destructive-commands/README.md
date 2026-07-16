# Block destructive commands

PreToolUse hooks that block dangerous Bash commands while still allowing normal operations.

## What's blocked

| Pattern | Why |
|---------|-----|
| `rm` with recursive + force flags in any spelling (`-rf`, `-fr`, `-r -f`, `-Rf`, `--recursive --force`) targeting `~`, `$HOME` (quoted or unquoted), or `/` | Nuking your home or root directory |
| `git push --force` to main/master | Overwriting shared history; use `--force-with-lease` |
| `git reset --hard` | Discards uncommitted work silently |
| `chmod 777` | World-writable permissions; security risk |

## What's NOT blocked

- `rm -rf ./node_modules` or any project-relative path -- agents can still clean up
- `rm -rf ~/old-project` or `rm -rf /tmp/foo` -- specific paths under home or root are allowed; only the home/root directory itself is protected
- `rm file.txt` -- normal file deletion is fine
- `git push --force` to feature branches -- only main/master is protected
- `git reset --soft` / `git reset --mixed` -- only `--hard` is blocked

## Design philosophy

These hooks are deliberately narrow. They block the specific catastrophic patterns but don't interfere with normal agent cleanup work. An agent that needs to `rm -rf node_modules` or `rm -rf dist/` can still do so.

Each hook command reads the tool-use JSON from stdin and re-checks `.tool_input.command` itself, only emitting a deny decision when the pattern actually matches (the rm guards strip quotes first, so `rm -rf "$HOME"` can't slip through). The `if` conditions remain as a cheap pre-filter so no subprocess spawns for non-matching commands, but they are not relied on for correctness: some environments (native Windows bash, Copilot CLI) ignore `if` and run every entry on every Bash call, and an unconditional deny command would then block everything.

## Installation

Copy the hook entries from `settings.json.example` into your `~/.claude/settings.json` under `hooks.PreToolUse`.

If you already have a `PreToolUse` matcher for `Bash`, add the hook objects to the existing `hooks` array.
