# Implementing an approved design into an existing report

Rules for the moment a design stops being a picture and starts being a report. They are
technique-agnostic: they apply whether the design arrived as a mockup you drew, a canvas someone
refined, an exported design file, or a screenshot on a whiteboard.

These were learned by getting them wrong. Each one has cost a session at least once.

## 1. Apply the delta only, and preserve existing chrome

The single most repeated correction. A design almost always arrives carrying more than the change it
was asked for: its own navigation, its own header, its own version of the filter pane, sometimes a
whole parallel design system. Applying it wholesale clobbers the shell the report already has.

- Implement **only** what the current request is about: the new page, the changed chart, the updated
  tokens. Nothing else.
- **Never replace** the existing left nav, page header, filter pane header row, or global layout
  unless the user explicitly asks, even when the incoming design includes its own versions of them.
- When an incoming component conflicts with the house design system, **keep the house version** and
  adapt the new component to it. The house system is the thing with continuity; the handoff is not.
- If the design implies a change to something global, say so and ask, rather than absorbing it
  silently as part of a page level change.

## 2. Scope-of-change discipline on shared objects

Report objects are shared far more than they look. A tooltip page, a theme text class, a measure used
for conditional formatting, a shared axis configuration: each may serve many visuals.

Before saving an edit to anything shared, check what else consumes it. Editing a shared tooltip page
to suit one chart silently changes every chart that points at it, and the damage shows up on a page
nobody opened during the change.

## 3. Verify before claiming done

An implementation is not done because the JSON is valid. It is done when it has been looked at.

- Run `pbir validate` on the report first. It catches schema breaks, not design breaks.
- Then run the screenshot loop in the **`pbi-verify-loop`** skill, using its mockup comparison so the
  rendered page is diffed against the design rather than against a memory of it.
- An agent cannot see the canvas. Any claim about how something looks, made without a screenshot, is
  a guess. Say "validated" when you validated and "verified" only when you looked.

## 4. Cleanup is deferred, not forced

Extraction and working folders frequently hold a file lock while a process still has them open.
Repeated delete attempts have failed three times in a row before now, and fighting the lock wastes
the session.

Attempt one delete at the **end** of the session. If it is locked, leave it in the scratchpad
directory, which is cleaned up automatically, and say plainly that it was left behind. Never loop on
a failing delete.

## 5. The reverse brief: asking for the next design round

When the next round of design work is needed, write a brief rather than a request. The brief exists
so the designer, human or otherwise, is working from the **current** state of the report rather than
from the state it was in when the last handoff was produced.

Write it into the project's `design-system/` folder, named `<TOPIC>-BRIEF.md`, matching any existing
naming convention in that project. Template below.

The three parts that matter most, because they are the ones most often missing:

1. **What changed since the last round.** New measures with their display folders, new pages, moved
   or renamed things. A designer working from a stale model designs for fields that no longer exist.
2. **The data actually available**, with types, formats, ranges and sample values. A design that
   assumes a percentage where the model has a count is a redesign, not a handoff.
3. **What must not be redesigned.** Name the chrome explicitly. This is the counterpart to rule 1 and
   it is what prevents the next handoff arriving with a fresh navigation bar.

State the canvas size explicitly. A design drawn at the wrong dimensions cannot be implemented
faithfully at any level of effort.

## Template

```markdown
# <TOPIC>: Design Brief

> Handoff from the implementation side. Everything below reflects the CURRENT state of the
> report after the latest changes.

## What changed since the last design round
- <model changes: new tables and measures, with display folders>
- <report changes: new pages, moved visuals, renamed sections>

## What we need designed
<One paragraph: the specific page, visual or KPI to design, its audience, and the question it
answers.>

### Data available for it
| Field / Measure | Type | Notes (format, range, sample values) |
|---|---|---|
| | | |

## Constraints: do not redesign these
- Keep the existing navigation, page header and filter pane header row exactly as they are.
- Use the existing design tokens; no new palette.
- Canvas: <exact pixel dimensions>.

## Deliverable
Only the NEW artifacts: the components, page spec, or token diff. Not a full design system
re-export.
```
