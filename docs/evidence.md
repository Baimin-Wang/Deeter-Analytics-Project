# Evidence protocol: v4

The target is Friday closing resolution of a Thursday-known contracting base, not a fixed 2% return. All entry features use data through Thursday close; impulse ATR and volume baselines end before the entire impulse. Outcome levels use Thursday's known 20-session ATR and the base's high/low. See `definitions.md` and `config/rules.json` for the formulas.

The PM list is generated before any Friday outcome is known. For each ticker, the screen tries a five-, four-, three- and two-session base in that order, keeps the longest candidate that passes the complete impulse and base definition, assigns a lean, and emits the row. It does not select a top-N subset or rank by subsequent performance. `outputs/latest_screen.csv` is therefore an audit table of all qualifying rows at the chosen as-of date; a PM-facing shortlist or position-sizing layer would be an additional policy that must be specified separately.

## Main sample and controls

Run 104 completed Thursday/Friday calendar pairs by default, roughly two years. Keep all requested Thursdays in `coverage.csv`, including zero-setup dates and missing-Friday outcomes. Use `--weeks 26` only for a quick smoke check; it is not the preferred evidence window. Each observation is one ticker setup per Thursday; multiple names and dates may share exposures. Observations are not independent trades.

`observations.csv` exports every accepted setup, all filter inputs, base-resolution outcome, boundary touches, overnight return and Friday-session return. `summary.csv` reports ALL_SETUPS, each lean and lean-by-original-direction groups. ALL_SETUPS contains the subgroups; it is not an independent control. The always-stall reference is the observed STALLS fraction, illustrating class imbalance rather than reporting the accuracy of a trained classifier. A high closing-stall share does not imply small intraday movement.

`impulse_only_observations.csv` and its summary/coverage are an additional reference: the same eligible equities, impulse and participation rules, 2-5-session age search and longest-qualifying tie rule, but no contraction, width, retention or extension filters. One observation per ticker/Thursday is retained. Dropping the base tests can change the chosen endpoint, direction and high-low window. Wider windows make resolution mechanically harder, so these rates are not a clean comparison of predictive value; return distributions provide another descriptive check. This reference is overlapping and unmatched, not a causal experiment.

## Sensitivity without winner selection

`--sensitivity` runs the default plus four predeclared one-at-a-time changes, writing every result to `sensitivity.csv`:

- Minimum impulse displacement: 2.5 or 3.5 pre-move ATR, versus default 3.0.
- Maximum mean-TR contraction ratio: 0.50 or 0.80, versus default 0.65.

All other settings stay fixed and all variants use the same input dates and outcome definition. This checks local sensitivity in two dimensions; it does not establish robustness of all parameters. Do not select the best-performing variant from this table. The effective default rules are serialized in `manifest.json`; variant overrides are recorded in the sensitivity table.

## What verification means

Synthetic checks cover a nonempty setup's invariance to future mutation/truncation, pre-impulse baseline timing, low liquidity despite high relative activity, a single volume spike, price churn, high absolute movement relative to a high-volatility background, failure to contract, deep retracement, scale invariance, down-move symmetry, missing ticker bars, boundary equality, overnight/intraday disagreement and missing Fridays. These establish implementation behavior, not a market edge.

The evidence remains limited by a manually selected universe, 17 unavailable or invalid tickers in the expanded download, missing delistings, unverified corporate-action adjustments, correlated samples and post-v1/v2/v3 researcher choices. V4 is not an untouched holdout. ATR normalization makes rules relative to prior ranges; it does not prove predictive power or correct every volatility-regime difference.

Daily OHLCV can identify closing resolution, high/low touches and open-to-close changes. It cannot establish ordering when both boundaries are touched, exact entry fills, spread, market impact, borrow or news timing. Direction-adjusted returns are diagnostics, not net short or long strategy returns. Raw overnight and session returns compound; their signed means need not add exactly to the total signed mean.

The next research step is to freeze definitions, agree the PM's equity universe and evaluate a later untouched period. Historical membership and verified corporate actions address sample integrity; timestamped intraday quotes, fills and borrow address execution; timestamped news or attention data addresses the "everyone is excited" interpretation. No p-values or profitability claim are reported.
