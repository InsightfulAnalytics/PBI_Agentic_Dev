# Layout, tables and the browser check

Found on a nine-page app checked at 390 to 2860 px in both themes, on `@microsoft/fabric-visuals`,
`fabric-datagrid` and `fabric-visuals-extensibility` 5.0.0 (1 Nov 2026).

Retest: `npm ls @microsoft/fabric-datagrid @microsoft/fabric-visuals-extensibility`, then run
`scripts/inspect-layout.js` on a page with a grid and open Show as table on a chart.

## fabric-datagrid: set each column's `width`

The grid lays its table out with `table-layout: fixed`, which ignores a column's `minWidth`, and it
keeps every header name on one line with an ellipsis. Nine columns at 1280 px came out equal and
cut "Segment" to "Se...". Give each column a `width` (and the same `minWidth`): the measured width
of its header name on two lines, plus about 80 px for the cell padding, sort icon and menu button.
Measure in the grid's font with a canvas `measureText`. Then let the name wrap:

```css
@layer components {
  .visual-frame [data-dg-header-label] { white-space: normal; }
}
```

A grid wider than its card then scrolls sideways inside it, which keeps every name whole.

## Show as table: hand it formatted text

VisualContainer's table view writes each cell with `String()` and ignores the column's format,
so 84.3% reads `0.8434657730971756`, and it lists every column of the query, sort keys included.
Pass the table through a formatter before it reaches the container: drop the label, sort-key and
order columns, and write each cell as text in its column's format (a month as "Mar 2025").

## The header toolbar: overlay it on the title's first line

VisualContainer shows Copy visual and More actions by widening its in-flow header toolbar from 0
to about 70 px on hover and focus, so a title that wraps re-wraps and the chart below it moves.
Reserving the toolbar's width in flow stops the jump but narrows every title at rest. To keep the
full width, position the toolbar over the end of the title's first line and fade it in, and float
an empty spacer of the toolbar's size at the end of that line so only the first line makes room:

```css
@layer components {
  .visual-frame [vc-toolbar=""] {
    position: absolute; inset-inline-end: var(--spacing-l);
    top: calc(var(--spacing-l) + (var(--leading-400) - var(--icon-size-500)) / 2);
    width: auto; margin: 0; overflow: visible; opacity: 0; transition: opacity 150ms ease-out;
  }
  .visual-frame:hover [vc-toolbar=""],
  .visual-frame:focus-within [vc-toolbar=""],
  .visual-frame [vc-toolbar=""]:has([aria-expanded="true"]) { opacity: 1; }
  .visual-frame .toolbar-room {
    float: right; width: calc(2 * var(--icon-size-500) + var(--spacing-xxs));
    height: var(--leading-400); margin-inline-start: var(--spacing-m);
  }
}
```

The spacer is an `aria-hidden` span placed first inside the title element. The layer must come
after the library's in the cascade's declared order, so it wins whatever the library's selectors
weigh, and an open More actions menu keeps the toolbar showing.

## Widths: every breakpoint, not the one on your screen

- **Twelve grid columns overflow a phone.** `grid-cols-12` with a 32 px gap needs 352 px for its
  eleven gaps alone. Use one column below `xl` and `col-span-full` spans.
- **A third of the canvas is under 300 px until `2xl`.** From 1280 to 1535 px, three cards in a
  row are 287 to 380 px wide, too narrow for row names plus value labels. Give the first of three
  the whole row until `2xl` and halve the next two.
- **Fixed card heights squeeze charts on phones**, where the title and subject wrap to many lines.
  Apply the fixed height from `xl` only and let the card grow below it. A chart whose labels need
  fixed room either side declares a `minWidth` and scrolls sideways inside a narrower card.
- **Lines and buttons that come and go move everything below them**: a refetch status line, a
  Clear all button, a progress row. Position them absolutely in a gap that is already there.
- **Native `<option>` lists open on the browser's own surface**, which can stay light in dark mode
  while the options inherit light text. Give `option` the popover background and foreground.

## The browser layout check

The build and the tests pass a page whose labels collide. `scripts/inspect-layout.js` checks a
rendered page: inject it with a browser tool's JavaScript call, then `window.__inspect()` returns
the page's issues. It reports text over text, SVG text cut at its SVG edge or ending in an ellipsis,
labels crossing a mark's edge, contrast under 4.5:1 (3:1 for large text) on the colour actually
behind the text, HTML text cut by its box, a chart wider than its card, a page that scrolls
sideways, `NaN`, `undefined` or `null` in the text, and error and loading states.

- `window.__runAll(["Overview", "Trends"])` visits each page through its `nav` button and
  inspects it; `window.__summary()` groups the issues once `window.__runOut.done` is true.
- Run it at 390, 768, 1024, 1280, 1440, 1536, 1920 and 2860 px in both themes. A same-origin
  `<iframe>` of the app at a set width gives each breakpoint without resizing the window: inject
  the script into `iframe.contentWindow`.
- A long run outlasts a browser tool's script timeout: start it, return, and poll `__runOut`.
- Right after a theme switch the colour transition reads as low contrast for a second or two in a
  throttled tab: wait before inspecting.

## Unit tests in jsdom

jsdom has no `matchMedia`, canvas or `scrollTo`. A media-query hook returns false without
`matchMedia`, a text-width helper estimates from character counts without a canvas, and the app
test stubs `window.scrollTo`.
