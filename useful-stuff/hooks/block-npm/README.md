# Block npm, suggest bun

A PreToolUse hook that blocks all `npm` commands and tells the agent to use `bun` instead.

## Why

- **Supply chain attacks.** npm runs post-install scripts by default. A compromised package can execute arbitrary code the moment you `npm install` it. Bun does not run post-install scripts by default, eliminating this attack vector.
- **Agent safety.** Agents auto-approve installs. With npm, that means auto-approving arbitrary script execution from every transitive dependency. Bun makes installs safe by default.
- **Speed.** Bun is also significantly faster than npm for installs, which matters in agentic workflows where packages get installed frequently.

## How it works

The hook command reads the tool-use JSON from stdin, extracts `.tool_input.command` with jq, and only emits a JSON deny decision (`permissionDecision: "deny"`) when the command actually invokes `npm` (at the start of the command or after `;`, `&&`, `||`); otherwise it outputs nothing and exits 0. The `if` condition (`Bash(*npm *)`) remains as a cheap pre-filter, but the command re-checks its own trigger because some environments (native Windows bash, Copilot CLI) ignore `if` and run every matcher entry on every Bash call -- an unconditional deny command would then block all Bash commands.

## Installation

Copy the hook entry into your `~/.claude/settings.json` under `hooks.PreToolUse`. See `settings.json.example` for the full structure.

If you already have a `PreToolUse` matcher for `Bash`, add the hook object to the existing `hooks` array rather than creating a duplicate matcher.
