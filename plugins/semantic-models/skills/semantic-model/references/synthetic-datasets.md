# Synthetic demo datasets

How to build a mock dataset for a Power BI demo, a lab or a performance test, when the user asks for
one. The aim is data that exercises real modelling (slicers, time intelligence, multi-fact analysis)
and is still pleasant to demo on: themed, with a story in it, and modelled correctly for BI from the
first row, never a flat dump.

## Shape

- **A star or galaxy schema.** Integer surrogate keys, dimensions conformed across facts, and a proper
  date dimension with a `yyyymmdd` integer key, marked as the date table (the
  `semantic-models:date-table` skill builds one).
- **No blank foreign keys.** Give every dimension an explicit "Not Applicable" member (key 0) and
  point unmatched fact rows at it.
- **One sign convention.** Store amounts positive and carry the sign on the account dimension (a
  `NaturalSign` column), or the reverse, but say which in the data dictionary.

## Generator

- **A seeded, zero-dependency script.** Python's standard library (`csv`, `random`, `datetime`) with a
  fixed seed, so it re-runs anywhere without installing anything and produces identical rows each
  time. Put the knobs (date range, row volumes, effect sizes) in a block at the top.
- **Build the story into the generator.** Growth ramps, seasonality, a few planted events, and causal
  links between facts (an incident drives a repair cost which drives a budget spike, with a lag) so
  analysis finds something real. Compute the drivers first and let the dependent tables read them;
  facts generated independently off a shared trend produce correlations that vanish once detrended.
  Keep each planted effect behind a knob that can be set to zero.
- **Size to the request.** Ask whether it is a demo (thousands of rows) or a stress test (hundreds of
  thousands to tens of millions), and generate to that.

## Ship alongside it

- **A validator** that checks every fact foreign key resolves to a dimension row, primary keys are
  unique, and basic sanity holds. Run it before handing over.
- **A data dictionary** (`README.md`): schema diagram, relationship table, columns per table, the sign
  convention, the planted story, and a few starter measures.
- Watch out for engineered outliers in ratio measures: one extreme event can swamp hundreds of
  routine ones, which is a good Simpson's-paradox teaching point and a bad headline number. Say which
  in the dictionary.
