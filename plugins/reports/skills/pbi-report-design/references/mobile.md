# Mobile Layout: Phone View as a Curated Subset

Power BI does not reflow a desktop page onto a phone. The portrait view is a hand-picked subset re-placed on a fixed narrow portrait grid. A visual appears in portrait only if it has a `mobile.json` alongside its `visual.json`. This inverts the desktop default: on the web every visual renders; on a phone nothing renders until explicitly opted in.

A page with no mobile-placed visuals falls back to rotated landscape, which is usually unreadable on a phone held in portrait.

## Design Principles

Pick the few visuals that answer the headline question for a mobile reader: KPI cards, the one primary chart, the key slicer. Wide tables, scatter charts, and dense matrices rarely survive the narrow portrait grid. Stack vertically with the answer at the top. Lay slicers and navigation buttons horizontally so they consume one short band rather than stacking tall.

**Build the phone layout alongside the desktop page** so a page copy duplicates placements from the start rather than being retrofitted.

## File Mechanics

The phone layout is stored per-visual, not per-page. Each visual folder may hold a `mobile.json` beside its `visual.json` (validated by the `visualContainerMobileState` schema). Required keys are `$schema` and `position`; the `position` block uses the same field names as desktop (`x, y, z, height, width, tabOrder, angle`) but in the phone-canvas coordinate space, which is independent of the desktop canvas.

"The page has a phone layout" is emergent: it is true if at least one visual has a `mobile.json`.

Inspect and set via the CLI:
```bash
pbir visuals mobile "Report.Report/Page.Page/Visual.Visual" --show
pbir visuals mobile "Report.Report/Page.Page/Visual.Visual" \
  --x 10 --y 5 --width 80 --height 20 --tab-order 1
```

Never hand-write `mobile.json`; let `pbir` preserve its schema and coordinate semantics.

## What to Include and Exclude

Rank visuals by their value for the mobile reader's primary question, then place the top 4-8 in a single column. Record which visuals you intentionally excluded. The over-faithful miniature anti-pattern (placing everything) produces a portrait page that scrolls forever and is harder to read than the rotated landscape fallback.

Keep mobile visuals simple enough that the report theme and ordinary visual formatting work on both
surfaces. If a mobile-only formatting operation is not exposed by `pbir`, report the gap instead
of editing `mobile.json`.

## Pitfalls

- A page that looks mobile-ready in the editor but has zero `mobile.json` files silently falls back to rotated landscape
- Mobile-optimized views render only in native iOS/Android apps; a browser (Service, Playwright, Chrome) always shows the landscape layout, so you cannot verify the portrait layout by browser screenshot
- Desktop and phone positions are independent; use `pbir visuals position` and
  `pbir visuals mobile` respectively
- Delete a visual with `pbir rm` so its mobile state is removed with it
- Absence of `mobile.json` is not automatically a defect; tie severity to intent (a headline KPI page with no mobile layout is high severity; a back-of-house detail page is usually fine)

## Publish to web ignores the mobile layout

Publish to web does not support mobile layout views: they are item 20 in its considerations and
limitations ([Publish to web from Power BI](https://learn.microsoft.com/power-bi/collaborate-share/service-publish-to-web#considerations-and-limitations)).
A public embed on a phone shows the desktop page shrunk to the screen's width, so a `mobile.json`
layout is wasted on a report meant for a website.

For a public report that has to read on a phone, build a second report on the same semantic model
with narrow pages (about 400 px wide, as tall as the content; FitToWidth scales it to the phone),
publish both, and let the website choose the embed by screen width (a CSS media query or a
`matchMedia` check that swaps the iframe `src`). Design that report as its own layout: one column,
navigation and filters in a band across the top, every chart the full width. Generate both reports
from one source of card definitions when you can, so a change reaches both. Retest: the
limitations list on that page still names Mobile layout views (checked 2026-11-02).
