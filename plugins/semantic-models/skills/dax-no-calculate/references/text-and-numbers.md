# Text and Numbers

From *DAX For Humans* Ch. 4 (Text) and Ch. 5 (Numbers). The recurring move is the same:
when DAX lacks a function, **build a table and aggregate** rather than reaching for a black
box.

## Numbers — essentials and gotchas

**Aggregate with the X versions** so you can iterate any table:
`SUMX, AVERAGEX, MINX, MAXX, COUNTX, STDEVX.P/.S, VARX.P/.S, MEDIANX`. (`.P` = whole
population, `.S` = sample.) Standard deviation = √variance.

**Safe division** — use `DIVIDE( num, den, BLANK() )` unless the divisor is a constant; it
guards divide-by-zero. For the integer part:
- `INT( DIVIDE( num, den, BLANK() ) )` for non-negative,
- `TRUNC( DIVIDE( num, den, BLANK() ) )` when negatives are possible — because `INT(-2.1) = -3`
  but `TRUNC(-2.1) = -2`. Prefer `TRUNC` over `QUOTIENT` (which lacks the error parameter).

**`=` vs `==` and BLANK:** `0 = BLANK()` is **true**, but `0 == BLANK()` is **false**. Use
strict `==` when you must distinguish a real zero from a blank. (Knowing 0 ≡ blank saves
hours of debugging.)

**Rounding family** (know the differences): `INT`, `TRUNC`, `ROUND`, `ROUNDDOWN`, `ROUNDUP`,
`MROUND` (nearest multiple), `CEILING`, `ISO.CEILING`, `FLOOR`, `EVEN`, `ODD`, `CURRENCY`.

**Trig & powers:** `SIN/COS/TAN/COT` (+ `H` hyperbolic, + `A` inverse) expect **radians** —
convert with `RADIANS()` or `* PI()/180`. `SQRT(x)` ≡ `POWER(x, 0.5)`.

### Patterns the book builds because DAX lacks the function

- **A better MOD / a better MEDIAN** — wrap the quirky built-ins (or rebuild with
  `MEDIANX`) to behave as expected on edge cases.
- **Mode** (no native function): group values, count occurrences, return the most frequent.
  ```DAX
  Mode =
      VAR __Counts = SUMMARIZE( Data, Data[Value], "__n", COUNTROWS( Data ) )
      VAR __Max    = MAXX( __Counts, [__n] )
      VAR __Result = MAXX( FILTER( __Counts, [__n] = __Max ), Data[Value] )
      RETURN __Result
  ```
- **Ranking without RANKX black-box behavior** — count how many rows beat the current one:
  ```DAX
  Rank =
      VAR __Me    = [Total Sales]
      VAR __Table = SUMMARIZECOLUMNS( Dim[Item], "__v", [Total Sales] )
      VAR __Result = COUNTROWS( FILTER( __Table, [__v] > __Me ) ) + 1
      RETURN __Result
  ```
- **Weighted average** — `DIVIDE( SUMX( T, weight * value ), SUMX( T, weight ) )`.
- **Linear interpolation** — find the bracketing rows (double lookup on the X column), then
  interpolate Y with the slope between them.
- **Simple linear regression** — compute slope/intercept from the least-squares formulas
  built out of `SUMX` over the points (`n`, `Σx`, `Σy`, `Σxy`, `Σx²`); a tidy demonstration
  that statistics reduce to a few `SUMX`es.
- **Aggregating measures** — when you need to aggregate a measure across a grain, summarize
  to that grain first then `SUMX`/`AVERAGEX` (same engine as the Measure Totals fix).

**Formatting numbers:** `FORMAT( value, "#,0.00" )` and friends; remember `FORMAT` returns
**text** (kills numeric sorting/aggregation), so format in the visual where possible and use
`FORMAT` only when you truly need a string.

## Text — extract, build, and tabulate

**Core functions:** `LEN`, `LEFT`, `RIGHT`, `MID`, `FIND`/`SEARCH` (SEARCH is
case-insensitive and supports wildcards), `SUBSTITUTE`, `REPLACE`, `UPPER`/`LOWER`/`PROPER`,
`TRIM`, `CONCATENATE`/`&`, `CONCATENATEX`, `REPT`, `UNICHAR`/`UNICODE`, `VALUE`, `FORMAT`.

Recipes in the chapter (all No-CALCULATE):

- **Extracting text** — pull a substring between delimiters using `FIND`/`SEARCH` + `MID`;
  the chapter revisits this with a more robust generalized approach later.
- **Counting occurrences** of a substring — compare `LEN` before/after `SUBSTITUTE`ing the
  needle out, divided by the needle length.
- **Replace from right** — there's no `RIGHT`-anchored replace; build it from `LEN` + `FIND`
  arithmetic.
- **Dynamic text** — assemble narrative/labels from measures with `&` and `SWITCH`; basis
  for dynamic titles and "smart narrative"-style captions.
- **Simple greeting / conditional formatting** — return text or hex colors from logic;
  drive a visual's conditional formatting from a measure.
- **Text → table** — split a delimited string into rows: generate an index table, then
  `MID`/`FIND` each segment (the DAX equivalent of `SPLIT`).
- **Preserving case / Anonymous** — case-aware transforms; anonymizing/masking text.
- **Phone number verifier** — validate/normalize formats with `SUBSTITUTE` + length/▢digit
  checks, returning a boolean or cleaned string.

> Theme across both chapters: where a function is missing (mode, split, gamma, networkdays),
> the No-CALCULATE answer is **construct a table that represents the problem and aggregate
> over it** — not hunt for a magic function.
