# Data triage before planning

Run this before any planning, theming, mockups or tickets on a dataset you did not build: a
competition or challenge dataset, a vendor extract, anything with a brief that asserts findings.
Report the verdict and let the user decide whether the build is worth doing **before** design work
starts.

**Why it comes first.** On one challenge the whole design tree was built before anyone looked hard at
the data: theme prototype, decision records, glossary, claim ledger, a published mockup, two audits.
The data then turned out to be entirely fabricated, with no relationship anywhere in it, and the
three findings its brief asserted did not exist in the shipped files. Every artefact was sound and
every one pointed at nothing. Ten minutes of the checks below would have caught it.

## The fabrication tells

- **Unit-blind shared ranges.** Several fields drawn on the same range regardless of unit: minutes,
  degrees, km/h and currency all on 0 to 1000.
- **Uniformity.** Real quantities are not uniform. Test each measure against a uniform CDF with a
  DKW confidence band.
- **Round synthetic bounds.** Ranges such as 500 to 150,000, 0 to 35, 1 to 10, 1 to 5 covering 99% or
  more of the observed span.
- **Universal independence.** Compute the full correlation matrix. A maximum absolute r near the
  noise half-width across every pair means there is no model underneath.
- **Placeholder keys.** `val_N` strings, or ids matching one template on every row.
- **Impossible values.** Minutes above 59, food above boiling, a rider at 500 km/h.
- **Derived columns that were not derived.** A weekend flag disagreeing with its own weekday column,
  a region contradicting the name field, child rows predating their parent's open date.
- **Allocation ramps.** A per-day count that is nearly constant with one short day at the end of the
  range is a fill-to-count loop, not a draw.
- **The brief against the data.** If the brief asserts specific findings, test each one before
  believing it.

## Writing a "cannot use this column" verdict

An audit verdict that a column is unusable must say **which question** it answers no to, with a
computed figure for each:

1. Can it be **displayed**?
2. Can a **relationship** be asserted from it?
3. Can the data be **grouped by** it?

These have different answers and different evidence bars. Collapsing them into one refusal
over-reaches invisibly: in one audit the relationship refusal held for 12 of 12 columns, but the
display refusal was too broad for 10 of 12 and the group-by refusal for 7 of 7, and 45 of 47 columns
turned out usable somewhere.

- A column can be statistically uninformative and still perfectly displayable. A flat distribution
  on a truthful axis with a non-causal caption is a finished visual, not a failure.
- Only physical impossibility genuinely bars a column from the canvas; statistical emptiness is a much
  weaker objection.
- Label self-contradiction is a separate failure from emptiness, and it is per table: test each
  dimension for a safe key before distrusting every label.
- A supported null is a finding. State it with its p-value and equivalence bound rather than reaching
  for a manufactured trend.
