# Calculation groups

Companion to the `semantic-model` skill (SKILL.md). Original guidance; each section cites its sources.

**Working with `te`:** `te add calculationGroup "Time Intelligence" --save`, then `te add calculationItem ...`. Read / set group precedence with `te set <group> -q precedence`; selection expressions, `selectionExpressionBehavior`, and variant guards that `te set` does not expose go through `te script` (TOM).

## Only one measure axis per visual: the second one has to be a calculation group

A measure field parameter occupies the Values well, so one visual dispatches measures from a field parameter **or** from a calculation group, never from two field parameters. A second measure axis, an Actual / Budget / Variance column set beside a parameter-driven row measure, has to be a calculation group. Decide this before building: the default failure is authoring a second field parameter, then finding in the report that it has no well to dispatch from.

In TMDL the items are children of `calculationGroup`, and an item's `formatStringDefinition = <dax>` is a child object under the item, separated from the item's scalar properties by a blank line; exact placement is in the `pbip:tmdl` skill, `references/authoring-gotchas.md`. The report-side binding (the expanded projections, the `fieldParameters` array, values-as-rows) is `pbip:pbir-format` territory, `references/visual-json.md` (Field Parameters).

Sources: `<repo>/examples/pl-switch-lab/` (PL Bridge Demo)

## Calculation group precedence: how items actually combine

When two calc groups have an item in filter context at once, the engine nests them: each item's `SELECTEDMEASURE()` token is textually replaced by the next-lower-precedence item's DAX, down to the base measure. The group with the **highest** `precedence` integer is the **outermost** wrapper. The output is order-dependent and rarely commutative ; a high-precedence `SELECTEDMEASURE()*2` over a lower `SELECTEDMEASURE()+2` on measure=10 gives `((10)+2)*2 = 24`, not 14. When a higher-precedence item uses `CALCULATE`/context transition, it rewrites the filter context the inner item sees (Time Intelligence at higher precedence makes YTD wrap both numerator and day-count denominator of an average). Precedence also decides whose dynamic format string wins: only the highest group's `formatStringDefinition` is evaluated, and a measure's own dynamic format string ranks below every calc group, though the winning item can still reach it through `SELECTEDMEASUREFORMATSTRING()` (see below).

Precedence lives on the **group** (not per-item `ordinal`, which is only within-group sort order ; do not confuse them, and see *Item order comes from declaration order* below for where that ordinal gets its value). Inspect with `te set <group> -q precedence` before setting; assign distinct integers when groups co-occur in one visual, or apply order is undefined. If `te set` cannot reach it, fall to a `te script` C# pass (`CalculationGroupPrecedence`) or edit the `precedence:` line in TMDL last. A calc item only modifies an expression containing a measure reference; with no `SELECTEDMEASURE()` in scope it is a no-op.

### Two groups: whose format string wins, and the base-measure escape hatch

With two groups in filter context at once, only the higher-precedence group's `formatStringDefinition` is evaluated. The lower group's format strings are never consulted at all, so the intuitive design (outer group swaps scenario, inner group sets units) silently loses the inner group's formatting: the numbers change, the units do not.

`SELECTEDMEASUREFORMATSTRING()` inside the winning item does not recover it. It returns the **base measure's** format string, not the lower group's, so an author reaching for it to inherit the inner group's units gets the wrong string, with no error anywhere.

To vary format by the inner group, put a dynamic format string on the **base measure** that reads the inner group's column with `SELECTEDVALUE`:

```dax
SWITCH (
    SELECTEDVALUE ( 'Unit Group'[Unit] ),
    "Thousands", "#,0,\K",
    "Millions",  "#,0,,\M",
    "#,0"
)
```

That moves the decision somewhere both groups can see. The base measure's own format string still loses on precedence; it is what the winning item's `SELECTEDMEASUREFORMATSTRING()` resolves to, which is exactly what makes the escape hatch work. The cost is one more dynamic format string and the per-cell evaluation that comes with it (`semantic-models:dax-optimisation`, `references/dax-performance-optimization.md`).

### Sharing one format-string implementation: a DAX UDF in `formatStringDefinition`

Calling a user-defined function from a calculation item's `formatStringDefinition` is supported and cheap. It is the maintainable way to share one format-string implementation across many items instead of duplicating a `SWITCH` in each of them, and it is the same move the variant trap below wants.

Read the cost correctly: the UDF call is small next to the ordinary per-cell format-string evaluation it sits on top of, and that evaluation is charged once per rendered cell rather than once per query. DAX UDFs need `compatibilityLevel: 1702` and a recent Power BI Desktop, and older AMO / TOM tooling throws `UnsupportedObjectType` on a `function` object, so a `te script` or `TmdlSerializer` pass can fail over a model Desktop opens happily (`pbip:tmdl`, `references/authoring-gotchas.md`).

### Item order comes from declaration order, not an explicit `ordinal:`

TMDL folder deserialization derives each item's ordinal from file order. A calculation group file containing **zero** `ordinal:` lines still comes back with ordinals 0..N matching declaration order, through `TmdlSerializer::DeserializeDatabaseFromFolder` and in the live model alike: `<repo>/examples/pl-switch-lab/PL Bridge Demo.SemanticModel/definition/tables/P&L View.tmdl` declares 14 items, carries no `ordinal:` line anywhere, and yields 0..13 in file order.

So declare the items in the order you want them shown and do not fight the serializer over it. Power BI Desktop **strips** an explicit `ordinal:` on save because it is redundant, so a generator's ordinals vanishing on the first save is not a regression. The hierarchy-level advice in `references/hierarchies-cultures.md` does not transfer here: reordering an existing hierarchy does mean setting `Ordinal` explicitly, reordering calc items does not. (Corrected 2026-08-24. The older belief that an item without an explicit ordinal defaults to -1 is wrong for the TMDL path; it may still hold for items added through TOM, which is untested.)

Sources: learn.microsoft.com calculation-groups (precedence); repo SpaceParts Z04CG1 Time Intelligence.tmdl; repo te-cli semantic-modeling-practices

## Row measures feeding a scenario-swapping group must be scenario-agnostic

A calculation item applies its filter **outside** the measure it wraps, so an inner `CALCULATE` filter inside the row measure beats the item's outer one and the scenario swap silently does nothing: every scenario column shows the same number, and nothing errors. Write the row measures with no scenario filter of their own and let the calculation item supply it.

Test the swap explicitly. Put two different calculation items side by side over the same row measure in one visual and confirm the numbers actually differ; a swap that does nothing is indistinguishable from a working one when only one column is on screen.

Sources: DAX filter-context semantics (an inner `CALCULATE` predicate overrides an outer filter on the same column); `<repo>/examples/pl-switch-lab/` (PL Bridge Demo)

## Calculation groups: sideways recursion (the only supported recursion)

A calc item can reference another item in the same group by overriding that group's column inside `CALCULATE` ; the one recursion form the engine permits. `YOY%` is built from the `YOY` and `PY` items (`DIVIDE(CALCULATE(SELECTEDMEASURE(), 'Time Intelligence'[Time Calculation]="YOY"), CALCULATE(SELECTEDMEASURE(), ...="PY"))`) rather than re-deriving them; a `PY YTD` item layers PY on top of the already-defined YTD item. This is composition for calc items: define `YTD`/`PY`/`YOY` once, then build derived items from them, and changing the base propagates. Each `DIVIDE` branch is a separate `CALCULATE` that re-enters the group cleanly.

Use the column's quoted full name inside the item DAX with the item name as a string literal ; this is the one place the literal is unavoidable, and the rename-safe `ISSELECTEDMEASURE` guidance does not apply (it is about measure references). So renaming a base item still requires a find-replace across dependent items. Only sideways recursion works; an item recursing into itself, or applying the same group twice in one `CALCULATE`, errors or is silently ignored (one item per group in filter context at a time). Nesting two overrides of the same group column in one `CALCULATE` collapses to the last filter.

Sources: learn.microsoft.com calculation-groups (sideways recursion, single-item-in-filter-context)

## Calculation groups: selection expressions and selectionExpressionBehavior

Two optional group-level DAX properties handle non-clean selections: `multipleOrEmptySelectionExpression` fires on multi-select, a nonexistent item, or a conflict; `noSelectionExpression` fires when the group is unfiltered. Each carries its own `formatStringDefinition`. Default when undefined: the group does not filter (base measure passes through); a single valid selection never triggers either. A model-level `selectionExpressionBehavior` (`Automatic` = today's `nonvisual`, or `visual`) tunes the default; above a future compat level `Automatic` resolves to `visual`.

Without `multipleOrEmptySelectionExpression`, a user multi-selecting calc-group items gets the unfiltered base measure with no signal ; a common "why is the number wrong" ticket. Define it to return a deliberate value (`BLANK()` with a `--`-style format) or block ambiguous selections; `noSelectionExpression` makes a "Current" default. These are group properties (confirm casing first); if `te set` does not expose them, use `te script` (`MultipleOrEmptySelectionExpression`, `SelectionExpressionBehavior`) or TMDL. Never put normal logic in these (they never fire on a single valid selection); each needs its own `formatStringDefinition` or it inherits a mismatching default (returning `BLANK()` but inheriting currency shows a stray symbol); `selectionExpressionBehavior=visual` changes existing report numbers, so baseline key measures before and after.

Sources: learn.microsoft.com calculation-groups (selection expressions)

## Calculation groups: hard limitations and the variant-data-type trap

Adding any calc group flips a model-wide switch. Unsupported alongside calc groups: OLS on the calc-group table; RLS on the calc group itself (use the data tables); Detail Rows Expressions; Smart Narrative; implicit column aggregations (the sigma options appear but cannot apply unless `discourageImplicitMeasures=true`, which removes them cleanly). In Live Connection, dynamic format strings are not applied to report-level measures.

The variant trap: the moment a calc group exists, Power BI treats **every** measure as the variant type. This silently breaks any dynamic format string that reuses another measure's value, and breaks visuals when an item runs arithmetic on a non-numeric measure (dynamic titles, text measures): `Cannot convert value ... of type Text to type Numeric`. Removing all calc groups reverts measures to their real types. This is the most surprising side effect in a review because the failure surfaces in report visuals, not the model. Two fixes, in order: guard arithmetic items with `IF(ISNUMERIC(SELECTEDMEASURE()), ...)`, or coerce a reused format-string measure with `FORMAT([Dynamic format string], "")`; the preferred long-term fix moves shared format-string logic into a DAX UDF, sidestepping the coercion (dovetailing with the UDF-over-calc-group guidance; the cost and the compatibility floor are under *Sharing one format-string implementation* above). When reviewing a model with calc groups, proactively check text/title measures and measure-reusing dynamic format strings.

Sources: learn.microsoft.com calculation-groups (limitations, considerations); learn.microsoft.com desktop-dynamic-format-strings; repo te-cli semantic-modeling-practices
