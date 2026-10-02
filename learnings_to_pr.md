# Learnings: DAX UDFs that fail to load, and titling visuals

These notes come from building a PBIP report whose measures sit on DAX user-defined functions
(UDFs), with Deneb and core visuals. Every point was checked in Power BI Desktop unless it says
otherwise. Each section names the skill reference it belongs in, so the PR can move it there
(see `LEARNINGS.md`: one fact, one place).

## 1. DAX user-defined functions

### A function that calls a newly added function can fail to load

Belongs in: `pbip:tmdl` `references/authoring-gotchas.md`, next to "DAX UDFs need compatibility
level 1702", with a pointer from `semantic-models:dax-standard`.

**Symptom.** New helper functions are added to `functions.tmdl` and called from a function that
already existed. Every measure built on that existing function breaks at once:

- visuals show "Something's wrong with one or more fields", with a warning icon on the measures in
  the field well;
- the measure editor shows `Failed to resolve name 'Sales.Weighted'. It is not a valid table,
  variable, or function name.`

The name in the message is the calling function, not the helper. The caller failed to load, so
nothing can call it.

**What was observed.** Desktop added the new helpers to the end of the model. Its next save of
`functions.tmdl` put them below every existing function, including the caller. Two different helper
designs failed the same way:

- helpers taking `TABLE EXPR` parameters;
- helpers with no parameters, built only from patterns that already worked elsewhere in the same
  model (a filter table applied with `KEEPFILTERS`, a scalar `CALCULATE`).

Writing the helpers' logic inline in the caller fixed it. Every function that already worked called
only functions above it in the file.

**Rule.** A function calls only functions that sit above it in `functions.tmdl`. When a new helper
would be called from an existing function, write the logic inside the caller instead.

Not isolated: nobody tried only reordering the file (helper above caller, then a full close and
reopen of Desktop). So it is not known whether the order alone matters or whether "added in the same
change as the caller's edit" is the trigger. Until that is tested, inline the logic.

**How to see the real error.** The measure error only names the caller. In DAX query view, run:

```dax
EVALUATE INFO.USERDEFINEDFUNCTIONS()
```

It lists every function with its `State` and `ErrorMessage`. A non-empty `ErrorMessage` marks each
function that failed to load and says why.

### Offline checks passed both broken versions

Belongs in: `pbip:tmdl` `references/authoring-gotchas.md`, and step 5 of
`semantic-models:model-change`.

`te validate` reported 0 errors on both versions that failed in Desktop. Several independent review
agents also read the DAX against Microsoft Learn and concluded that both would run. Neither check sees
how Desktop orders and loads functions. [Tabular Editor CLI 0.7.1.2 preview. Verified 2026-09-30.]

Retest: `te validate` on a model where an existing function calls a function added below it.

After any change to `functions.tmdl`, treat the change as unproven until Desktop has loaded it and
`EVALUATE INFO.USERDEFINEDFUNCTIONS()` shows no `ErrorMessage`. Where there is no Desktop (a Linux
Codespace), say so in the handover and ask the user to run that query. Don't report the change as
working.

### Tabular Editor 3 before 3.24 marks `TABLE EXPR` as an error

Belongs in: `tabular-editor:te-docs`, and the UDF notes in `semantic-models:dax-standard`.

`( t : TABLE EXPR ) =>` is valid DAX: Microsoft Learn's page "DAX user-defined functions" uses it in
its `CountRowsLater` example. Older Tabular Editor 3 builds underline the type hint in red anyway.
Its release notes record the fix: "Our Semantic Analyzer will no longer show a false error when
using certain UDF parameter type hints in combinations that are valid, for example: `(a: TABLE EXPR)
=> ...`". In the same TE3, untyped `x : EXPR` parameters showed no error.

So a red line on a UDF signature in TE3 doesn't prove that Power BI rejects it. A clean TE3 editor
doesn't prove the function loads either (see above). Check the TE3 version under Help > About, and
check `INFO.USERDEFINEDFUNCTIONS()` in Desktop. [Fixed in TE3 3.24.0, October 2025. Verified 2026-09-30.]

Retest: in TE3, create a function `(a : TABLE EXPR) => a` and see whether the hint is underlined.

## 2. Title a visual with its own title and subtitle

Belongs in: `reports:pbi-report-design` (core rule), `pbip:pbir-format` `references/textbox.md` and
`references/visual-container-formatting.md`, and `custom-visuals:deneb-visuals`. Branch
`docs/visual-title-rule` already writes the rule into those files. This section adds what was learned
applying it.

**Rule.** Give a visual its title and subtitle through its own container `title` and `subTitle`. A
Deneb visual can use the same container slots, or its spec's `title` with `subtitle`. Don't place a
separate text box above the visual. Use a text box only for what those slots can't do:

- the page title;
- a section header over several visuals;
- a callout or note;
- a line with mixed formatting, such as a bold run or a measure-bound run;
- text that belongs to no single visual.

**PBIR.** The text goes in `visual.visualContainerObjects`. Literal text is single-quoted, and an
apostrophe inside it is doubled (`'Each store''s sales'`):

```json
"visualContainerObjects": {
  "title": [{ "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "text": { "expr": { "Literal": { "Value": "'Depth by month'" } } }
  } }],
  "subTitle": [{ "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "text": { "expr": { "Literal": { "Value": "'Number = weeks on promotion. Highlight = peak band.'" } } }
  } }]
}
```

Style the title and subtitle once, in the theme's `visualStyles["*"]["*"]`. Set `show: false`
there, so only the visuals that set `show: true` get a title:

```json
"title": [{ "show": false, "fontFamily": "Segoe UI Semibold", "fontSize": 18,
            "fontColor": { "solid": { "color": "#252423" } }, "alignment": "left", "titleWrap": true }],
"subTitle": [{ "show": false, "fontFamily": "Segoe UI", "fontSize": 12,
               "fontColor": { "solid": { "color": "#605E5C" } }, "alignment": "left", "titleWrap": true }]
```

**Applying it to an existing page:**

- Delete the title text box, then move the visual up to the text box's top. Also move it left or
  right to the text box's x, so the new title lines up where the old one was. The visual's body then
  sits at that x too, which can leave the left and right margins inside a card unequal. Either accept
  that or move the card's accent to match.
- A subtitle is one paragraph. A two-paragraph text box becomes one run of text, so rewrite it as one
  or two short sentences.
- Keep subtitles at 12 pt or more, in the theme and in any visual override. They are the smallest
  text on the page.
- `pbir add title` and `pbir add subtitle` add page-level text boxes. They don't set a visual's
  title.
- Alt text stays in `visualContainerObjects.general.altText`. Moving the title doesn't touch it.

**A check that keeps it true.** A report test can flag a text box that acts as one visual's title.
Flag it when it ends at most about 24 px above a single data visual (not a shape or button) and spans
at least half that visual's width. Also flag a text box that overlaps the visual's top edge: the
first version of the test only looked above the visual and missed the "laid over the top" case.
