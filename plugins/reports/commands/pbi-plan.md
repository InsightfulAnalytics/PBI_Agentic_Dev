---
name: pbi-plan
description: Plan or resume a multi-session Power BI report or model build as a numbered ticket map with an HTML plan board.
argument-hint: "[what you are building, or a path to an existing PLAN.md]"
model: opus
---

# Plan a Power BI build

## Arguments

$ARGUMENTS

## Instructions

Load the `reports:pbi-plan` skill and follow it. It is `disable-model-invocation: true`,
so this command is the only way in.

Then decide which of three jobs the argument is asking for.

### No `PLAN.md` exists yet, and the argument describes a build

1. **Check it is worth planning.** Apply the skill's "When to use this, and when not to".
   A single-page change or one measure does not get a plan. Say so, route to
   `reports:create-pbi-report` or `semantic-models:semantic-model`, and stop.
2. **Find the PBIP.** Locate the `.pbip` and its `.Report` / `.SemanticModel` folders. If
   the project does not exist yet, that is ticket 01.
3. **Interview before ticketing.** You need the audience, the deadline, what is explicitly
   out of scope, and what is already built. Ask what is genuinely unresolved, in one round
   of questions, and make ordinary judgement calls yourself.
4. **Write `PLAN.md`** at the project root, from `references/PLAN-template.md`. All four
   sections. The fog list names tooltips, navigation, theme and accessibility even when
   the answer is "none".
5. **Order the tickets by the skill's rule:** page tickets specify the measures, model
   tickets are `Blocked by:` the page ticket that consumes them, and the model skeleton is
   ticket 01.
6. **Every ticket gets an `Exit` line that is a command returning an exit code.** Use
   `--enforce` on `close-plan.py` in report tickets.
7. **Generate the board** and give the user the path:

   ```bash
   python <pbi-plan skill>/scripts/plan-board.py PLAN.md
   ```

8. Report the frontier. Do not start building unless the user asks.

### `PLAN.md` exists

Resume. Follow the skill's **Resuming** section: read the plan, reconcile it against the
PBIR and TMDL **on disk** rather than the transcript, correct any ticket whose status
disagrees with the files and say which ones you corrected, regenerate the board, then
report the frontier.

### The argument names a ticket number

Work that ticket per the skill's **Working a ticket**, but only if it is on the frontier.
If it is not, say what is blocking it and what the frontier actually is.

## Always

- The markdown is the source of truth. Never hand-edit `PLAN.html`; edit `PLAN.md` and
  re-run `plan-board.py`.
- Regenerate the board in the same change that alters any ticket status.
- Never renumber a ticket. Cut with `Status: cut`, add at the next free number.
