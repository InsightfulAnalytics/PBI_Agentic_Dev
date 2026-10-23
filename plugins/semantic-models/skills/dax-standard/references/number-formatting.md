# Number formatting: dynamic format strings + UDFs

Detail for the Number formatting section of [SKILL.md](../SKILL.md).

**Do not `FORMAT()` a measure to make it look right.** `FORMAT` returns *text*, so the
measure stops being a number — charts, sorting and aggregation all break. Format the
**number** instead, with a **dynamic format string** on the measure, and put the repeated
formatting logic in a **user-defined function** so it is written once.

## Rule: a measure has `formatString` OR `formatStringDefinition` — never both

They are mutually exclusive. A measure carrying both makes Power BI Desktop refuse to open
the whole project ("not supported scenario"). **To use a dynamic format string the static
format string must be absent** — delete the `formatString:` line.

In TMDL, `formatStringDefinition` is a **child object, not a property**: it goes *after* the
scalar properties, separated by a blank line, expression inline on the same line.

```tmdl
/// Revenue, auto-scaled to K / M / B for the value on screen.
measure 'Total Revenue' =

		SUM ( Sales[Amount] )
	displayFolder: Sales
	lineageTag: <guid>

	formatStringDefinition = Fmt.Scaled ( SELECTEDMEASURE (), 1 )
```

`SELECTEDMEASURE()` is the value being rendered; referencing the measure by name
(`[Total Revenue]`) also works, but breaks once a calculation group is in the model (every
measure becomes *variant*). Prefer `SELECTEDMEASURE()`.

## The UDF: write the formatting convention once

[DAX user-defined functions](https://www.sqlbi.com/articles/introducing-user-defined-functions-in-dax/)
(Power BI Desktop September 2025+, compatibility level 1702+) hold the scaling/currency rules
in one place instead of a copy-pasted format expression per measure — this is what Microsoft's
own dynamic-format-string docs recommend. Syntax is `name = ( params ) => body`; each
parameter is typed (`NUMERIC`, `INT64`, `STRING`, `TABLE`, …) and takes a passing mode:
`VAL` (evaluated once, in the caller's context) or `EXPR` (lazy, re-evaluated inside the
body — needed for measure references and anything context-sensitive).

Functions live in `functions.tmdl` in the model definition:

```tmdl
/// Scale-aware format string: K / M / B, with `decimals` decimal places.
function 'Fmt.Scaled' =
		(
			value: NUMERIC VAL,
			decimals: INT64 VAL
		) =>

		// The unit comes from the magnitude of the value being displayed.
		VAR __Abs = ABS ( value )
		// "0" repeated = the decimal placeholders.
		VAR __Dp = REPT ( "0", decimals )
		VAR __Result =
			SWITCH (
				TRUE (),
				__Abs >= 1E9, "#,0." & __Dp & ",,,""B""",
				__Abs >= 1E6, "#,0." & __Dp & ",,""M""",
				__Abs >= 1E3, "#,0." & __Dp & ",""K""",
				"#,0." & __Dp
			)
		RETURN
			__Result
```

Every measure that needs it then gets a one-line `formatStringDefinition`. One function per
formatting *convention* (scaled, currency, percent, duration) — not one per measure. Check
[daxlib.org](https://daxlib.org) before writing one; installing packages is covered by
`pbi-desktop:connect-pbid` (`references/daxlib.md`).

**Before one function calls another**, read the UDF load traps in `pbip:tmdl`
`references/authoring-gotchas.md`. A function that called a helper added below it in
`functions.tmdl` failed to load in Desktop, the error named the caller rather than the helper, and
`te validate` passed it. Until that is isolated, write new helper logic inline in the existing
caller. After any `functions.tmdl` change, run `EVALUATE INFO.USERDEFINEDFUNCTIONS()` and read
`ErrorMessage` before calling the change done. A red underline under `TABLE EXPR` in Tabular
Editor 3 is not proof of an error either (`tabular-editor:te-docs`).

## Gotchas

- The expression must return **text**, and it is evaluated per cell in that cell's filter
  context — which is what lets it react to a currency slicer or to the magnitude of the value.
- **Visual display units override it.** If a scaled format "does nothing", set the visual's
  *Display units* from **Auto** to **None** (or turn them off report-wide in the theme).
- A calculation group's format-string expression wins over the measure's own.
- Dynamic format strings only work on **model** measures — not report-level measures in a
  live-connect report.
