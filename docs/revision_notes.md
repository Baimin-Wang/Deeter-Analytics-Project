# Revision notes: v4

V3 made the rule definitions more coherent but still used a 56-name demonstration cache and a 26-pair, roughly six-month evidence window. The user asked why the definitions had their effects, how positive and negative cases behave, why the pool was small, and why the history was short. V4 addresses those questions in the executable project.

Changes:

- Expanded `config/universe.csv` from 56 to 448 manually curated US-listed equity tickers across sectors. Preserved the original list in `config/universe_56.csv`.
- Downloaded the expanded daily history where Yahoo Finance returned usable data. The cache now has 431 usable names; 15 tickers returned no usable history and two files had one row, so all 17 are reported and excluded rather than silently filled.
- Changed the backtest default from 26 to 104 completed Thursday/Friday pairs, about two years. The six-month setting was an execution-time choice for the original four-hour prototype, not an economic or data requirement. The old 26-pair v3 output is preserved in `outputs/legacy_v3_26`.
- Added a concrete positive/negative example for each definition in `docs/definitions.md`: price and capacity, ATR-scaled impulse, path efficiency, distributed volume, contraction, retention, continuation/failure lean, buffered Friday resolution, and overnight versus Friday-session behavior.
- Added explicit explanation of why each rule exists and what its synthetic tests prove. The tests establish implementation semantics; they do not establish market effectiveness.
- Added universe validation, requested-versus-loaded counts, skipped-ticker summaries, and the loaded-universe size to `manifest.json`.
- Reran the latest screen and two-year backtest on the expanded usable pool. Results and the PM note now report the actual 431-name data coverage and 104-pair window.

The default rules themselves remain the v3 relative-impulse/base rules: the universe and evidence horizon changed in v4, while the rule values remain explicit hypotheses. This keeps the effect of expanding the pool and lengthening the sample distinguishable from another threshold search.

The current two-year result has 604 evaluated bases: 81 GOES_AGAIN, 432 STALLS and 91 FAILS. This is more informative than 19 observations from the old 56-name six-month run, but the sample is still correlated and selected. The continuation-watch group has negative mean direction-adjusted Friday returns; the broader sample therefore does not validate the lean.

The cache starts in January 2024 for the original fixture and mostly in April 2024 for the expanded download. A request for 156 weeks will include dates that cannot form all baselines; those dates remain visible in `coverage.csv`. A genuine longer history requires fetching earlier bars and, for a production study, point-in-time membership, delisted names and a controlled corporate-action policy.
