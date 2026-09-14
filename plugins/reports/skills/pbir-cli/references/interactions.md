# Interactions: tooltip pages, navigation, and hit targets

The report **shell**: the layer that is not a chart and not the model, and the layer a signed-off
artboard almost never covers. Tooltip pages, page navigation, reachability and hit targets get
retro-fitted onto a locked design unless they are decided while the design is still open.

**Most of the mechanics are already documented elsewhere. Read those first; this file carries only
what they do not.**

| You need | Read |
|---|---|
| Tooltip page JSON: `type: "Tooltip"`, `visualTooltip`, `section`, canvas size | `pbip:pbir-format` skill, `references/page.md` (Tooltip Pages) |
| Whether to build a tooltip page at all, and how to design it | `reports:pbi-report-design` skill, `references/tooltips-and-annotations.md` |
| Wiring cross-filter overrides and adding a `pageNavigator` | `reports:create-pbi-report` skill, `references/interactivity.md` |
| Button actions (`PageNavigation`, `Back`, `Bookmark`, `Drillthrough`) | [bookmarks.md](./bookmarks.md), [cli-reference.md](./cli-reference.md) |

The single most common failure with tooltip pages is not a JSON error. It is hand-authoring one
without reading `pbir-format`'s `references/page.md` first, and discovering `type: 'ReportPage'`
is accepted as a string and silently ignored.

## The tooltip filter context trap

A report-page tooltip inherits **every column the raising visual projects into that data point**,
not just the field you hovered. Hover a bar in a chart sliced by Genre and Year, and the tooltip
page evaluates under both.

That is usually what you want, and occasionally catastrophic: a measure on the tooltip that is meant
to show a **share of total** or a **rank within the whole set** silently computes within the hovered
slice instead. It does not error, does not render blank, and returns a plausible number. The
Netflix build shipped a tooltip panel whose percentage was of the hovered slice rather than the
catalogue, and it read as correct in every screenshot.

**The fix is at authoring time, in the measure, not in the tooltip page:**

```dax
-- Wrong on a tooltip: the hover's slice is already in filter context
Share of Catalogue = DIVIDE ( [Titles], CALCULATE ( [Titles], ALLSELECTED ( 'Title' ) ) )

-- Right: state the denominator explicitly so the hover cannot narrow it
Share of Catalogue = DIVIDE ( [Titles], CALCULATE ( [Titles], ALL ( 'Title' ) ) )
```

**The test:** for every measure on a tooltip page, name its denominator out loud. If the answer is
"all titles" but the measure does not say `ALL` or `REMOVEFILTERS`, it is wrong. This is test 3 of
the insight test in `reports:pbi-report-design`, applied to the one surface where the wrong answer
is invisible.

Related and already documented: never put a page-level `filterConfig` on a tooltip page. The hover
**is** the filter, and a page filter compounds with it.

## Deneb: a line mark has no per-row hover

A Vega-Lite `line` mark renders one path per series, so there is nothing per-row to hover. The
tooltip fires on the whole line or not at all, and `pbiFormat` on a line's tooltip channel appears
to do nothing. The same is true of `area` and of `rule` drawn as a single mark.

Add an invisible point layer over the line and let that carry the hover:

```json
{
  "layer": [
    {"mark": {"type": "line", "strokeWidth": 2}},
    {
      "mark": {"type": "point", "filled": true, "size": 60, "fillOpacity": 0},
      "encoding": {"tooltip": [{"field": "Month", "type": "temporal"}, {"field": "Titles", "type": "quantitative"}]}
    }
  ]
}
```

### `fillOpacity: 0` hit-tests; `fill: "none"` does not

This is the trick that makes the layer above work, and it is not obvious.

- `"fillOpacity": 0` draws a fully transparent fill that **is still in the hit-test tree**. Hover
  and click both land on it.
- `"fill": "none"` draws no fill at all. There is nothing to hit, the pointer passes straight
  through, and the tooltip never fires.

The same distinction governs any deliberate hit target: an oversized transparent `rect` behind a
sparse scatter, a wider invisible band over a thin rule, a padded hit area on a small mark. Always
`fillOpacity: 0`, never `fill: "none"`.

Deneb cross-filter selection obeys the same rule, so an invisible hit layer is also how you make a
thin or sparse mark selectable. See the `custom-visuals:deneb-visuals` skill for the selection and
`pbiColor` mechanics themselves.

## Tooltip page sizing

`displayOption: "ActualSize"` is mandatory on a tooltip page: tooltip pages do not scale, so a page
authored at `FitToPage` renders at whatever pixel size the container gives it and the layout drifts.
Design at final pixels. 320x240 is the default, 400x120 reads well for a wide compact strip.

One tooltip page can serve many visuals. Set `section` on each raising visual to the same page
`name` rather than cloning the page.

## Reachability: the check nobody runs

A page with no navigation affordance pointing at it is reachable only through the page tab strip,
and a report published with hidden tabs is then unreachable entirely. Tooltip and drillthrough
pages are the deliberate exception; every other page needs a route in.

Two things make a page reachable:

- a `pageNavigator` visual, which auto-syncs to the visible page list, or
- an `actionButton` (or shape, or image) with `--type PageNavigation --target "<page name>"`

```bash
pbir visuals action "Overview.Page/Nav Details.Visual" --type PageNavigation --target "Details"
```

Prefer the navigator. N hand-built buttons are N blobs to re-point on every page add or rename, and
a stale `target` does not fail validation.

**Decide the shell before the design locks.** Navigation, tooltip pages, a sources or method page,
footers and alt text are report-level chrome that page artboards do not cover, so each one is an
addition to a signed-off design if it is raised later. The `reports:pbi-plan` skill makes naming
these axes a required step, and `scripts/close-plan.py` in this skill sweeps a finished `.Report`
for the ones left undecided:

```bash
python scripts/close-plan.py "Sales.Report"
```
