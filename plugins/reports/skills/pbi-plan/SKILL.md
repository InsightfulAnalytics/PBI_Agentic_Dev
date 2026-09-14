---
name: pbi-plan
version: 26.26
description: Plan a multi-session Power BI report or model build as a numbered ticket map with an HTML plan board. Use when the user asks to plan a build, map out a report, or resume a build that spans more than one session. User-invoked only, via /pbi-plan.
disable-model-invocation: true
---

<!--
The ticket shape (numbered tickets carrying Type / Status / Blocked by, a frontier rule,
a "fog of war" list of what is not yet specified, and an explicit out-of-scope section) is
adapted from Matt Pocock's `wayfinder` and `to-tickets` skills, MIT licensed.

MIT License. Copyright (c) 2026 Matt Pocock.
Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify, merge,
publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons
to whom the Software is furnished to do so, subject to the following conditions: the above
copyright notice and this permission notice shall be included in all copies or substantial
portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
USE OR OTHER DEALINGS IN THE SOFTWARE.

See ATTRIBUTIONS.md at the repo root.
-->

# Planning a Power BI build

> **Work in progress.** This skill has been used on one build. The ticket shape and the
> board are stable; the replanning and close-out sections are still being tuned against
> real builds. Treat its numbers as observations from one project, not as benchmarks.
> It never loads on its own: it is `disable-model-invocation: true` and runs only when
> the user types `/pbi-plan`.

A multi-session Power BI build fails in a specific way. It does not fail by producing a
wrong chart. It fails by losing the thread: session three rebuilds what session one
already shipped, a measure gets a second definition under a new name, and the surfaces
nobody drew (tooltips, navigation, alt text) arrive at the end as "small additions" to a
design that is already signed off.

This skill lays a map before the build starts, keeps it honest while the build runs, and
renders it as an HTML board the user can watch the journey on.

## When to use this, and when not to

**Use it when at least two of these are true:**

- The build spans more than one session.
- More than about six visuals, or more than one page.
- Model work and report work both have to happen, and one gates the other.
- There is a real audience and a real deadline, so scope creep costs something.

**Do not use it for:**

- A single-page change, a formatting pass, or one new measure. Go straight to
  `reports:create-pbi-report` or `semantic-models:semantic-model`. A plan for a
  twenty-minute job is overhead with a progress bar.
- Exploration. If the question is "what is in this data", explore first and plan after.
  A plan written before the data is understood is a list of guesses that then has to be
  defended.

**Hand-offs.** This skill plans. It does not build. Each ticket is executed by the skill
that owns that work:

| Ticket type | Executed by |
|---|---|
| `model` | `semantic-models:semantic-model`, `semantic-models:dax-standard`, `pbip:tmdl` |
| `page`, `visual` | `reports:create-pbi-report`, `reports:pbir-cli` |
| `design`, `chart choice` | `reports:pbi-report-design` (run the insight test there) |
| `deneb` | `custom-visuals:deneb-visuals`, `custom-visuals:deneb-pbir` |
| `shell` | `reports:pbir-cli`, its `references/interactions.md` |
| `theme` | `reports:power-bi-theme`, `reports:modifying-theme-json` |

## The map

One markdown file, `PLAN.md`, at the root of the PBIP project folder, beside the `.pbip`.
Not in a notes vault, not in a scratch directory: it is an operational file and it lives
with the thing it plans. Copy `references/PLAN-template.md` to start.

It has four parts, and all four are mandatory.

### 1. What this is for

One paragraph: what the build is for, and who reads the finished thing. If it cannot be
written, the plan is premature and the answer is to go and find out, not to start
ticketing.

### 2. Out of scope

Things a reasonable person might expect and will not get, each with its reason on the
line. RLS, mobile layout, scheduled refresh, a drillthrough hierarchy. This section is not
housekeeping. It is the thing you point at in week two when someone asks why there is no
mobile layout, and its absence is what turns that question into a day of work.

### 3. Not yet specified (the fog list)

Every question the build will have to answer and cannot answer yet. **Four entries are
mandatory and must appear even when the answer is "none":**

- **Tooltips**
- **Navigation**
- **Theme**
- **Accessibility**

These four are compulsory because they are invisible on a page artboard. Nobody draws a
tooltip in a mockup, so nobody signs one off, so every one of them arrives after the
design is locked and lands as a change rather than as work. Naming them up front, even to
write "Tooltips: none, default everywhere", converts a late surprise into an early
decision. `scripts/plan-board.py` reports a plan problem when any of the four is missing.

Add to the list whenever the build raises a question it cannot settle. **Removing an entry
means writing the answer into a ticket, not deleting the line.** A fog list that only ever
shrinks is a fog list nobody is using.

### 4. Tickets

Numbered from 01, and **never renumbered**. A number is an address that other tickets,
commit messages and conversations point at. Renumbering silently breaks every reference.
Cut work by setting `Status: cut`, never by deleting the ticket and closing the gap.

## Ticket shape

```markdown
### 07: Spend by category

Type: page
Status: open
Blocked by: 02, 05
Exit: `python <pbir-cli skill>/scripts/close-plan.py "Sales.Report" --enforce`

What to build: one horizontal bar chart, spend by category, sorted descending, top 12
plus an "other" band.

- [ ] passes the insight test
- [ ] title states the insight, not the shape
- [ ] tooltip decided, even if the decision is "default"
- [ ] alt text written
```

| Field | Rule |
|---|---|
| `Type` | `model`, `page`, `visual`, `design`, `deneb`, `shell`, `theme`, `data`. Routes the ticket to its skill. |
| `Status` | `open`, `in progress`, `done`, `cut`. `blocked` is never written by hand, it is derived. |
| `Blocked by` | Ticket numbers, or `none`. |
| `Exit` | **Mandatory. A command that returns an exit code.** |

### The `Exit` line is the part that matters

A ticket whose exit condition is prose closes when someone feels it is closed. A ticket
whose exit condition is a command closes when the command passes. Almost always one of:

```bash
pbir validate "Sales.Report"
python <pbir-cli skill>/scripts/close-plan.py "Sales.Report" --enforce
```

`close-plan.py` ships advisory by default and non-blocking is the right default for a
script anyone might run at 11pm. **The `--enforce` belongs here, in the ticket.** A gate
wired into twenty tickets runs twenty times; a gate hard-coded into a script's default
runs once and then gets deleted the first time it stops a legitimate ship.

For a model ticket, a DAX query that returns an expected value is a valid exit. For a
design ticket, the exit is the insight test in `reports:pbi-report-design` with its
verdict recorded in the ticket. "Looks right" is not an exit condition.

### Ordering: model tickets are blocked by the pages that consume them

The instinct is to build the model first and the pages after, so the pages depend on the
model. Invert it. Write the page ticket first, let it name the measures it needs, and make
the **model ticket `Blocked by:` the page ticket that specifies it.**

A measure written before anything consumes it is written against a guess at the filter
context. A measure written against a named visual has a denominator you can state out
loud, which is exactly what the insight test and the tooltip filter-context trap both turn
on. See `reports:pbir-cli` `references/interactions.md`.

The exception is the skeleton: the date table, the fact table and the one relationship.
That is ticket 01 and everything is blocked by it.

## The frontier

**The next ticket is the lowest-numbered ticket that is open, unblocked and unclaimed.**

Not the most interesting one, not the one adjacent to what was just finished. The rule
exists so that "what now" is never a judgement call at the start of a session, which is
precisely when context is thinnest and the temptation to re-decide the plan is strongest.

```bash
python <this skill>/scripts/plan-board.py PLAN.md --frontier
```

A ticket is blocked when any of its blockers is not `done` or `cut`. That is derived from
the `Blocked by` lines every time the board renders, so a blocked ticket cannot go stale.

**If the frontier is empty and work remains, every remaining ticket is blocked.** That is
a plan bug, not a work state: something upstream needs finishing, or a `Blocked by` line
is wrong. The board says so explicitly.

## The HTML plan board

Every plan gets a board. It is how the user follows the journey rather than reading a
markdown diff, and it is the reason the plan gets looked at between sessions at all.

```bash
python <this skill>/scripts/plan-board.py PLAN.md
# writes PLAN.html beside PLAN.md
```

Self-contained: one file, no CDN, no network, light and dark, and it prints. Open it with
`start PLAN.html` on Windows or `open PLAN.html` on macOS.

It shows:

- a progress bar and status counts across the whole build
- **Next up**, the frontier, with the single next ticket called out
- **The build**, a vertical timeline read top to bottom, so the journey reads in the order
  it will actually be worked. Wave markers punctuate the rail: everything under one marker
  has its blockers satisfied above it, so those tickets can be taken in any order, and
  nothing under the next marker can start until they are done. The rail node carries the
  status colour, so a scan down the left edge is a scan of progress. Each card carries its
  number, type, status, what it is blocked on, its acceptance criteria with a done count,
  and its `Exit` command.
- **Not yet specified** and **Out of scope**, side by side
- **Plan problems**, when a blocker points at a ticket that does not exist, when the
  dependency graph has a cycle, or when the fog list is missing one of its four mandatory
  axes

**Regenerate the board at the end of every ticket, in the same change that sets
`Status: done`.** The markdown is the source of truth and the board is a projection of it;
a board that lags the plan is worse than no board, because it is believed.

Never hand-write or hand-edit `PLAN.html`. Edit `PLAN.md` and re-run the script. Two
authors on one file is the same lost-edit class of bug as two writers on one PBIP.

## Working a ticket

1. Take the frontier ticket. Set `Status: in progress`, regenerate the board.
2. Route to the owning skill from the hand-off table. Build.
3. Run the `Exit` command. It must pass, and you must have seen it pass.
4. Tick the acceptance criteria that are genuinely met. An unticked box is information;
   a ticked box that is not true poisons the whole map.
5. Set `Status: done`, regenerate the board, and in the **same** change write any new
   question the ticket raised into the fog list.

Step 5 is the one that gets skipped and it is the one the plan lives or dies on. A
question discovered during a ticket and not written down is discovered again three
sessions later, from scratch.

## Resuming

At the start of a session that continues a build:

1. Read `PLAN.md`.
2. **Reconcile it against the PBIR and TMDL on disk, not against the transcript.** The
   files are what shipped. A plan is a claim about the files, and a resumed session that
   trusts the claim over the files will rebuild things that already exist and skip things
   that silently did not land.

   ```bash
   pbir tree "Sales.Report" -v
   python <pbir-cli skill>/scripts/close-plan.py "Sales.Report"
   ```

3. Correct any ticket whose status disagrees with the disk, and say which ones you
   corrected.
4. Regenerate the board, then take the frontier.

This step is not ceremony. Most of the divergence a long build accumulates shows up here,
and it takes two minutes to find and an afternoon to find later.

## Replanning

**Expect to rewrite a third of the plan during the build.** On the one multi-session build
this skill has been run against, the PBIR spec grew from 2,484 to 3,246 lines, and 31% of
the growth was correcting things the plan had asserted rather than adding new work. That
is not a planning failure. A plan written before the data is in Desktop cannot know what
the data will look like, and pretending otherwise is what produces plans nobody updates.

So replan deliberately, on a schedule, rather than defending the original:

- **Add** a ticket at the next free number. Never insert one between existing numbers.
- **Cut** with `Status: cut` and a one-line reason in the body. The number stays.
- **Split** an oversized ticket into new numbered tickets, set the original to `cut`, and
  make the new ones `Blocked by:` whatever the original was blocked by.
- **Never renumber.** Never silently change what a ticket meant. If the meaning changed,
  cut it and write a new one, so the map still explains what actually happened.

A plan whose tickets are all still `open` in session four is not a plan being followed. A
plan that has been edited every session is working exactly as intended.

## Close-out

Refuse to call the build finished while any of these is true:

- The frontier is not empty.
- Any ticket is `in progress`.
- The fog list has an entry that is not either answered in a ticket or moved to
  **Out of scope**.
- `close-plan.py` still reports undecided cells that nobody has ruled on. `not decided` is
  not a state a delivered report is allowed to be in. **"Off" is a decision; silence is
  not.**

Then run both exits one final time and regenerate the board, so the artefact that survives
the build is a complete and accurate record of it:

```bash
pbir validate "Sales.Report"
python <pbir-cli skill>/scripts/close-plan.py "Sales.Report" --enforce
python <this skill>/scripts/plan-board.py PLAN.md
```

Finally, write what the build taught into the project's `LEARNINGS.md`. The plan records
what was done. It does not record what was learned, and those are different files.

## Reference Files

```yaml
references/PLAN-template.md: a filled PLAN.md to copy, with the four mandatory sections and four worked tickets
scripts/plan-board.py: renders PLAN.md to a self-contained PLAN.html; --frontier prints the next tickets and any plan problems
```

Related skills: `reports:pbir-cli` (`scripts/close-plan.py`, `references/interactions.md`),
`reports:create-pbi-report`, `reports:pbi-report-design` (the insight test).
