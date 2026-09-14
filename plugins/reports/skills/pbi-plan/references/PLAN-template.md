# <Report or model name> build plan

**PBIP:** `<Name>.pbip`
**Started:** <YYYY-MM-DD>
**Status:** in progress

One paragraph: what this build is for, and who reads the finished thing. If you cannot
write it, the plan is premature.

## Out of scope

Named, so nobody re-opens it mid-build. Keep the reason on the line.

- Row-level security. Single audience, no sensitivity split.
- Mobile layout. Desktop and full-screen only.
- Scheduled refresh. The model reads a static extract.

## Not yet specified

The fog list. Every entry is something the build will have to answer and cannot answer
yet. **Four axes are mandatory and must appear even when the answer is "none",** because
each one is invisible on a page artboard and therefore arrives later as a scope change:

- **Tooltips:** not decided. Candidates are a canvas tooltip on the trend chart, default
  everywhere else.
- **Navigation:** not decided. Tab strip, or a `pageNavigator`, or per-page buttons.
- **Theme:** not decided. House theme or a bespoke palette.
- **Accessibility:** not decided. Alt text on every data visual is assumed; contrast
  target unconfirmed.
- **Denominator for "share of catalogue":** whole catalogue or the filtered slice.

Add to this list whenever the build raises a question it cannot settle. Removing an entry
means writing the answer into a ticket, not deleting the line.

## Tickets

Numbered, never renumbered. A ticket is a unit of work with an exit condition a machine
can check.

### 01: Date table and model skeleton

Type: model
Status: done
Blocked by: none
Exit: `pbir validate "<Name>.Report"`

What to build: the standard DimDate, the fact table, and the one relationship between them.

- [x] DimDate marked as a date table
- [x] relationship is single-direction, many-to-one
- [x] one measure resolves against it

### 02: Core measures

Type: model
Status: open
Blocked by: 01
Exit: `pbir validate "<Name>.Report"`

What to build: the base measures every page consumes, in house DAX style.

- [ ] each measure names its denominator explicitly
- [ ] format strings set
- [ ] no measure relies on an implicit filter that a tooltip could narrow

### 03: Overview page

Type: page
Status: open
Blocked by: 02
Exit: `python <pbir-cli skill>/scripts/close-plan.py "<Name>.Report" --enforce`

What to build: the KPI strip and the trend chart.

- [ ] every chart passes the insight test
- [ ] title states the insight, not the shape
- [ ] tooltip decided for every visual (a deliberate "off" counts)
- [ ] alt text written

### 04: Report shell

Type: shell
Status: open
Blocked by: 03
Exit: `python <pbir-cli skill>/scripts/close-plan.py "<Name>.Report" --enforce`

What to build: navigation, tooltip pages, the sources and method page, footers.

- [ ] every visible page has a route in
- [ ] every tooltip page is `ActualSize` and is raised by something
- [ ] the fog list is empty or every remaining entry is deliberate
