# TMDL Authoring Gotchas

The failure modes that a syntax reference does not catch.

**Do not accept "it parsed" as the check.** The worst TMDL mistakes deserialize cleanly and report
PARSE OK while the model is already wrong: an expression that swallows its own properties, a format
string that vanishes, a generator that doubles a table. Every rule below names the symptom string an
agent will actually be handed, and the check that settles it.

Everything here is universal, true of any host that reads the file, unless a line says otherwise.
Paths written `<repo>/...` are relative to the repository root; a bare `examples/...` path is relative
to this skill folder.

## Calculation groups require `discourageImplicitMeasures`

A calculation group anywhere in the model requires `discourageImplicitMeasures` on the model object
in `model.tmdl`. Without it Power BI Desktop refuses to load the **whole project**, not just the
calculation group.

```tmdl
model Sales
	culture: en-GB
	discourageImplicitMeasures
```

Check it every time a calculation group is added. It is the most repeated cause of a project that
will not open after a model change. Both shipped example models carry it beside their calculation
groups: this skill's `examples/SpaceParts.SemanticModel/definition/model.tmdl`, and
`<repo>/examples/pl-switch-lab/PL Bridge Demo.SemanticModel/definition/model.tmdl`.

Setting it also turns implicit aggregation off model-wide. After adding it, grep the report pages for
bare column projections that relied on an implicit measure (a column dropped straight into a Values
or Y well) and replace them with explicit measures before the project is reopened.

## `///` doc comments must carry the same indent as the object they describe

A `///` line at column 0 above a tab-indented `measure` declaration fails the parse with:

```
TMDL Format Error / Parsing error type - Indentation
```

The error names the **measure** line, not the comment, so the reported line number points at the
wrong place. (Verified 2026-08-24.)

```tmdl
	/// Actual minus Budget.
	measure 'P&L Var' =
			[P&L Actual] - [P&L Budget]
		displayFolder: 01 Fast P&L
		lineageTag: abc-123
```

A generator that builds a measure block as a list of strings must prefix the doc-comment lines with
the same indent it gives the declaration, not the declaration alone.

The companion rule is in SKILL.md `### Descriptions`: a `///` line is never followed by a blank line.
The error text for that one is `Unexpected line type: Empty!`, and it breaks a powerbi-modeling-mcp
`ConnectFolder` connection as well as a Desktop file open.

## A standalone `//` comment line is not a TMDL line

`//` is the comment syntax of DAX and of M, not of TMDL. Inside an expression body it is safe, because
it is stored as part of the expression text. Anywhere else the TOM deserializer refuses the file, and
the parsing error type is `InvalidLineType`:

| Where the `//` sits | Result |
| --- | --- |
| on a line of its own at column 0, between declarations | `Unexpected line type: Other!` |
| on a line of its own at any indent, between declarations | the same error |
| trailing a declaration, as in `table Product   // note` | the same error, because the parser reads the whole line as the object header |
| inside a DAX or M expression body | parses, and the comment travels with the expression |
| trailing a line that is already inside an expression body | parses, for the same reason |

```tmdl
	measure 'Margin %' =
			// safe: a DAX comment, part of the expression
			DIVIDE ( [Margin], [Revenue] )
		lineageTag: abc-123
```

Use `///` for anything that should survive as a description, and keep the rest of the commentary inside
an expression body. Both shipped example models do exactly that: every `//` in them sits in an M or DAX
body, in this skill's `examples/SpaceParts.SemanticModel/definition/functions.tmdl` and in
`<repo>/examples/pl-switch-lab/PL Bridge Demo.SemanticModel/definition/expressions.tmdl` and its
`functions.tmdl`.

A structural linter will not catch a misplaced `//`. The binaries in `<repo>/plugins/pbip/hooks/bin/` are
platform-suffixed, one per host (`tmdl-validate-linux-x64`, `tmdl-validate-darwin-arm64`,
`tmdl-validate-darwin-x64`, `tmdl-validate-windows-x64.exe`), and every one of them reports
`Valid TMDL (0 errors, 0 warnings)` on a file the deserializer refuses.

(Verified 2026-09-07 against the TOM `TmdlSerializer`, on a minimal model and on the shipped
`examples/SpaceParts.SemanticModel`. The same deserializer accepts the identical minimal model with the
`//` line taken out, so this is the TMDL grammar rather than a limitation of one assembly build. Power
BI Desktop's own parser was not tested, so treat a `//` line as unusable rather than as a
Desktop-specific limit.)

Retest: insert a `// comment` line of its own, at any indent, into a table `.tmdl` and run
`TmdlSerializer::DeserializeDatabaseFromFolder` over the `definition/` folder.

## Blank lines: only two spots break

Blank lines between sibling objects inside a table block are standard. Desktop emits them on save,
and a blank line before the first `annotation` is the canonical shape. Do not strip blank lines
wholesale to clear a parse error; that fights the serializer and destroys the annotation separation.

`Unexpected line type: Empty!` and `InvalidLineType: Empty` come from exactly two places:

1. a blank line directly after a `///` line;
2. a blank line that breaks a multi-line expression's indentation.

Work out which of the two you hit, and fix only that.

## A measure's expression sits one level deeper than its properties

Three tabs for the DAX, two for `displayFolder`, `lineageTag` and `formatStringDefinition`, one for
the `measure` declaration itself. Write the expression at the **same** depth as the properties and the
parser reads `displayFolder:` and every line after it as more DAX.

The failure is silent. `TmdlSerializer` still reports PARSE OK, the `formatStringDefinition`
disappears, and the measure's expression is quietly corrupt. (Verified 2026-08-28 on the PL Bridge
Demo model in `<repo>/examples/pl-switch-lab/`: a generator emitted 28 measures at two tabs, all 21 format
strings vanished, and nothing complained.)

The check is a round trip, not a parse. Deserialize the folder and assert what came back:

```powershell
$db = [Microsoft.AnalysisServices.Tabular.TmdlSerializer]::DeserializeDatabaseFromFolder($definition)
$t  = $db.Model.Tables['00_Measures']
$t.Measures.Count
($t.Measures | Where-Object FormatStringDefinition -ne $null).Count
$t.Measures['P&L Var'].Expression
```

Compare both counts and a sample `.Expression` against what was written. The
`pbi-desktop:connect-pbid` skill covers loading an assembly that can do this.

The round trip is not Windows-bound; only the host above is. The same
`TmdlSerializer::DeserializeDatabaseFromFolder` call runs on Linux and macOS against the `net6.0` or
`net8.0` build of the unified `Microsoft.AnalysisServices` NuGet package, under PowerShell 7 or a
`dotnet` console project. Tabular Editor's CLI deserializes the same folder without any of this, and
`references/bim-to-tmdl.md` covers driving it. What will not settle it is the platform-suffixed
`tmdl-validate-*` binaries bundled at `<repo>/plugins/pbip/hooks/bin/`: they are structural linters, and
they will not tell you a format string went missing.

## `formatStringDefinition` is a child object, not a property

`formatStringDefinition = <dax>` is a child object of the measure. It goes **after** the scalar
properties (`displayFolder`, `lineageTag`), separated from them by a blank line, and is followed by a
blank line before the next sibling object. Putting it between the scalar properties fails the parser.

Three body shapes are all valid:

- inline on the `=` line, for a one-line expression;
- an indented block, two levels deeper than the `formatStringDefinition` line (depth 4 when the
  measure is declared at depth 1);
- a triple-backtick block, opening fence on the `=` line and the closing fence at body depth.

A multi-line body at any other depth fails the parse.

```tmdl
	/// Actual for the selected period.
	measure 'P&L Actual' =
			CALCULATE ( [Amount], 'P&L View'[Scenario] = "Actual" )
		displayFolder: 01 Fast P&L
		lineageTag: abc-123

		formatStringDefinition = SWITCH ( TRUE (), ABS ( [P&L Actual] ) >= 1000000, "$#,##0,,.0""M""", "$#,##0" )

	/// Budget for the selected period.
	measure 'P&L Budget' = ...
```

Shipped examples of every shape: inline in
`<repo>/examples/pl-switch-lab/PL Bridge Demo.SemanticModel/definition/tables/00_Measures.tmdl`, indented
block and triple-backtick in this skill's
`examples/SpaceParts.SemanticModel/definition/tables/__Demo UDFs.tmdl`.

## A measure may not carry both `formatString` and `formatStringDefinition`

Power BI Desktop refuses the whole project with `not supported scenario` if a measure carries both.
The message names nothing useful, so it is hard to trace from the text alone. (Verified 2026-08-23.)

It bites in both directions: adding a dynamic format string to a measure that already had a static
`formatString:` and leaving the old property behind, and reverting to a static format without
deleting the `formatStringDefinition`. Remove the other one in the same edit.

It also bites on the way out of an indentation bug. A wrongly indented expression swallows the
`formatString:` line into the DAX (see above); correcting the indent later makes both properties live
at once. Whenever you fix an indentation bug, check the measure for both.

## Generators must strip by object name, never by line position

Power BI Desktop re-serializes a `.tmdl` file on save and **reorders** measures, so a start/end line
pair captured from an earlier layout can invert. `lines[:start] + lines[end:]` then silently
duplicates everything between them instead of removing it. (Seen 2026-08-24 on the PL Bridge Demo
model: a table went from 223 to 432 measures, half the file doubled, and the TMDL still parsed clean.)

Parse the file into named blocks, drop the blocks the generator owns, reinsert the new ones, and
assert the final count. Run the generator **twice** as an idempotency test, and hash both trees, model
and report: a generator that doubles measures passes a report-only hash without a flicker.

## What offline validation actually proves

A powerbi-modeling-mcp offline (`ConnectFolder`) connection validates parse and bind. It cannot run
DAX queries. A `TmdlSerializer` round trip proves the same two things and no more. The
`pbip-validator` agent does not parse TMDL at all; it delegates PBIR to `pbir validate` and inspects
TMDL by reading it.

Offline-clean is not query-correct. A measure can deserialize cleanly, bind to real columns, and still
return the wrong number or error at query time. Prove behaviour against real data separately: a live
instance through the `pbi-desktop:connect-pbid` skill, or an XMLA endpoint.

## DAX UDFs need compatibility level 1702

DAX user-defined functions in `functions.tmdl` require `compatibilityLevel: 1702` in `database.tmdl`,
and Power BI Desktop 26.06 or later to open the project.

Symptom: `TmdlSerializer::DeserializeDatabaseFromFolder` throws `UnsupportedObjectType` on `function`,
or `Model.Functions.Add` throws `CompatibilityViolationException`. That is the AMO/TOM assembly doing
the reading being older than DAX UDF support, not a broken model. Check the **assembly** version of the
loaded `Microsoft.AnalysisServices.Tabular` before editing anything, and do not treat a valid model as
corrupt:

```powershell
[System.Reflection.AssemblyName]::GetAssemblyName($dllPath).Version
```

Read the assembly version, not the file version: they disagree. (Observed against the AMO assembly
bundled with DAX Studio, assembly version 19.84.1.0, whose file version reads 16.0.142.20, so a file
version will not match anything documented here. The newer unified `Microsoft.AnalysisServices`
package, 19.114.x, ships `net6.0` and `net8.0` assemblies and may lift the limit.)

The shipped `examples/SpaceParts.SemanticModel` is the worked case. With that older assembly it fails on
its DAX UDFs and gets no further: `Unsupported object type - function is not a supported property in the
current context!` at `./functions` line 1. Nothing else in the model is reached, so read that error as
the assembly predating UDFs, not as a defect in the model.

Retest: build the `pbi-desktop:connect-pbid` skill's `scripts/daxlib-tom` project against the current
`Microsoft.AnalysisServices` package, then deserialize a `definition/` folder that contains a
`functions.tmdl`. A clean round trip retires the workaround below.

Workaround while the assembly cannot read them: copy `definition/` to a scratch folder, delete
`functions.tmdl` from the copy, and validate the copy.
`<repo>/examples/pl-switch-lab/scripts/demo/validate_model.ps1` does exactly this, and the PL Bridge
Demo model round-trips clean once stripped, 16 tables deserialized.

It does not rescue every model. Stripping `functions.tmdl` from `examples/SpaceParts.SemanticModel` gets
that model past the UDF error and straight into a second one,
`Property 'description' is unknown and is not expected in the situation it appears.`, even though no file
in it declares an explicit `description` property. So an older assembly can leave a model with no offline
route at all. A parse error naming something the model plainly uses correctly is the signal: upgrade the
assembly rather than chasing the model.

For the UDFs themselves the referee is a parser that understands 1702: Power BI Desktop 26.06+ on
Windows, or, where Desktop is unavailable, an XMLA deploy of the model to a workspace on a capacity
that supports compatibility level 1702, which fails the deploy with the same authority.

## Prefer `///` over an explicit `description` property

An explicit `description` property is valid TMDL, but `///` is what Power BI Desktop serializes.
Author descriptions as `///` so the first Desktop save does not rewrite them and round-trip diffs stay
stable.

## Adding to this file

This file is the in-repo home for TMDL authoring failure modes. A new one goes here rather than in a
per-machine notes file, in the same shape as the rules above: the verbatim symptom string, the
mechanism, and the check that settles it. `LEARNINGS.md` at the repo root decides where a fact goes
when it is not about TMDL.
