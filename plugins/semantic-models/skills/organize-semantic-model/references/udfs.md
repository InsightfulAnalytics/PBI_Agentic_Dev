# DAX user-defined functions

Reference for the UDF pass of the `organize-semantic-model` skill.

## When a UDF earns its place

- The same logic is repeated across several measures with only a measure or column swapped: a time-intelligence window, a "full month" or "dates with data" filter, a currency conversion, a dynamic format string, an SVG visual
- A business rule should live in one place so changing it changes every measure at once
- Not for a single measure's one-off logic; a UDF that is called once is indirection with no reuse

Propose candidate UDFs to the user with the measures they would replace. Refactoring measures onto a UDF changes their expressions, so show the before and after and verify the results match with a DAX query before and after.

## Requirements and objects

- Compatibility level 1702 or higher. Raising it is one-way; ask before doing it
- In a Tabular Editor script: `Model.AddFunction("Name", "( params ) => body")` returns a `Function` with `Description`, `Expression`, `IsHidden` and annotations. `Model.Functions` enumerates them
- In TMDL they live in `definition/functions.tmdl`

## Naming

Use compound, dot-separated names that say where the function comes from and what it does: `TimeIntelligence.MonthToDate`, `FormatString.Component.DecimalPlaces`, `DaxLib.Convert.CelsiusToFahrenheit`. DAX has no namespaces, so the full name is always typed at the call site. Tabular Editor's BPA rule "Use compound names for user-defined functions" flags single-word names, and Tabular Editor 3 groups functions by those segments in the TOM Explorer; its `Namespace` property changes that grouping only, never the callable name.

## Syntax

```
FUNCTION <Name> = ( <param> [: [type] [subtype] [mode]] [= <default>], ... ) => <body>
```

- Types: value types `AnyVal` (default), `Scalar`, `Table`; reference types `AnyRef`, `ColumnRef`, `MeasureRef`, `TableRef`, `CalendarRef`
- Scalar subtypes: `Variant`, `Int64`, `Decimal`, `Double`, `String`, `DateTime`, `Boolean`, `Numeric`
- Modes: `val` evaluates the argument once in the caller's context (default for value types); `expr` passes it unevaluated so the function decides the context (required for reference types). A measure passed as `val` is already evaluated and ignores any `CALCULATE` inside the function, which is the usual reason to declare `expr`
- `= <default>` makes a parameter optional; callers skip it with an empty argument (`F(1,,3)`)
- Type hints are worth writing: they make call sites fail loudly and document intent

## Documenting a UDF

Two layers, both expected:

1. `///` lines above the function in TMDL or DAX query view become the function's description (what it returns, one line per parameter)
2. `//` comments inside the parameter list explain each parameter: what it expects, valid values, an example argument. Inside the body, put a `//` line before each step, as the `dax-standard` house style does for measures

### Example: Microsoft Learn (DAX query view)

```dax
DEFINE
    /// AddTax takes in amount and returns amount including tax
    FUNCTION AddTax = (
            amount : NUMERIC
        ) =>
        amount * 1.1

EVALUATE
{ AddTax ( 10 ) }
```

### Example: model-specific time intelligence (SpaceParts)

```tmdl
function 'TimeIntelligence.MonthToDate' = ```
		// Cumulate month-to-date only for dates with sales
		(
		    measureReference: EXPR
		)
		=>
		    CALCULATE (
		        measureReference,
		        CALCULATETABLE (
		            DATESMTD ( 'Date'[Date] ),
		            'Date'[IsDateInScope]
		        )
		    )
		```
```

`EXPR` matters here: the measure must be evaluated under the month-to-date filter, not before it.

### Example: library component with parameter comments (DaxLib.FormatString in SpaceParts)

```tmdl
function 'FormatString.Component.DecimalPlaces' = ```
		// Returns a 0 string repeated a number of times equal to the number of decimal places
		(
		    // Base format string
		    // Expects a valid format string base, i.e. "#,##0"
		    base_format: STRING,

		    // Number of decimal places
		    // Expects an integer value from 0-9
		    decimal_places: INT64
		)
		=>
		    base_format
		    &
		    IF (
		        decimal_places > 0,
		        "."
		            & REPT ( "0", MIN ( decimal_places, 9 ) ),
		        ""
		    )
		```

	annotation DAXLIB_PackageId = DaxLib.FormatString

	annotation DAXLIB_PackageVersion = 1.0.0-beta
```

Functions installed from DaxLib carry `DAXLIB_PackageId` and `DAXLIB_PackageVersion` annotations. Keep them; they are how the package is recognized and updated. Do not rename or edit a packaged function in place; wrap it in a model function instead.

More examples: `plugins/pbip/skills/tmdl/examples/SpaceParts.SemanticModel/definition/functions.tmdl` in this repo.

Sources: learn.microsoft.com/dax/best-practices/dax-user-defined-functions; learn.microsoft.com/dax/function-statement-dax; docs.tabulareditor.com/en/tutorials/udfs.html; docs.tabulareditor.com/en/kb/bpa-udf-use-compound-names.html
