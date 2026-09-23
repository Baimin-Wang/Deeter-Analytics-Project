# Deeter Analytics: quant research working project

V4 screens for a directional move that is large relative to the stock's normal range, accompanied by participation across the move, followed by a contracting base that retains the move. The lean is a conditional watch near a base boundary. Friday evidence tests closing resolution of that base and reports Friday-session returns separately.

## Reproduce the supplied run

Use Python 3.10+ from the repository root:

```bash
python -m venv .venv
# Activate the environment, then:
python -m pip install -r requirements.txt
python -m src.run_screen --offline --end 2026-09-21
python -m src.backtest --offline --end 2026-09-21 --weeks 104 --sensitivity
python -m unittest discover -s tests -v
```

PowerShell activation: `.venv\Scripts\Activate.ps1`. macOS/Linux: `source .venv/bin/activate`. The commands use the local cache without network calls. The expanded universe has 448 names, of which 431 currently have usable cached histories; the 17 unavailable or invalid names are reported. The default backtest now covers 104 completed Thursday/Friday pairs (about two years), rather than the old 26-pair prototype window. Current results are exploratory and unfavorable to a predictive claim; see `docs/evidence_results.md`.

Remove `--offline` to permit Yahoo Finance public endpoint downloads. No API key is required. Default runs exclude the current UTC date conservatively, potentially lagging a just-completed US session. The actual as-of date is printed. A latest-close result on a non-Thursday is a preview, not the requested historical Thursday-night watchlist. For example, use `--end 2026-09-17 --output outputs/thursday_screen.csv` to inspect that Thursday.

Use `--universe path/to/equities.csv` to supply the agreed equity universe (a `ticker` column is required), or `--symbols AAPL MSFT NVDA` to select names. `config/universe.csv` now contains 448 manually curated US-listed equity tickers across sectors; `config/universe_56.csv` preserves the original fixture. The cache is now broad enough for 431 of the 448 names, but it is still a downloaded research snapshot rather than a point-in-time universe. With `--offline`, unavailable names are reported and skipped; with network access, the loader downloads them. V4 has no cross-sectional rank gate: changing pool size does not change the price-activity hurdle for a name. The union of observed dates is used to check missing ticker sessions, so calendar coverage still matters. The code does not independently verify security type or historical universe membership.

## Definitions are executable

Defaults live in `config/rules.json`; pass `--rules path/to/rules.json` for an explicit alternative. The full formulas, reasons and ambiguities are in `docs/definitions.md`, which replaces the old 6% / top-quartile / endpoint-volume / 2%-7%-4% rule set.

- Eligibility: price at least $5 and median dollar volume at least $20m, measured before the impulse and again at the screen. These are provisional liquidity assumptions.
- Impulse: five-session net displacement at least 3 pre-move ATRs, with at least 60% closing-path efficiency. ATR uses mean daily true range over 20 sessions, not a statistical z-score.
- Participation: mean impulse volume at least 1.5 times the preceding 60-session median and at least three of five days at or above that median.
- Base: 2-5 sessions; mean true range at most 65% of the impulse's; total width and largest daily true range each at most 1.5 pre-move ATRs; worst intraday retention at least half the impulse; extension no more than another quarter of it.
- Lean: `CONTINUATION_WATCH` or `FAILURE_RISK` only when within 0.25 current ATR of the relevant base edge and the latest close moved toward it. For an UP impulse, the upper base edge is the continuation boundary and the lower edge is the failure boundary; for a DOWN impulse, the lower edge is the continuation boundary and the upper edge is the failure boundary. Otherwise `UNRESOLVED`. No probability or weighted volume score.
- Outcome: GOES_AGAIN or FAILS when Friday closes beyond the corresponding base boundary plus a 0.10 Thursday-ATR buffer; otherwise STALLS (no confirmed closing resolution). Friday-session movement of at least 0.50 Thursday ATR is separately classified, with raw and signed return windows retained.

The numbers are explicit hypotheses, not estimates of optimal cutoffs. The included sensitivity run varies the impulse and contraction hurdles one at a time and publishes every result without selecting a winner. An impulse-only reference omits base filters; its endpoints and window geometry can differ, so it is not a matched causal control. The former six-month window was a speed choice for the first prototype, not a data limit; the default is now two years and the available cache covers materially more than six months.

## Current assumptions

This is a transparent first-pass research definition. The assumptions below are deliberate choices that make the PM brief executable; they are not claims that the thresholds are optimal.

| Area | Current assumption | Why it is used | What it does not prove |
|---|---|---|---|
| PM language | “Everyone is excited” is proxied by an unusual, directional price move with broad volume participation. The screen allows both UP and DOWN impulses because the stated book can be long/short. | Daily OHLCV can measure abnormal activity and participation without pretending to observe sentiment. | It does not measure how many people are paying attention, news tone, social discussion or buyer/seller imbalance. |
| Universe | 448 manually curated US-listed equity tickers are requested; 431 currently have usable histories. Price must be at least $5 and median dollar volume at least $20m before the impulse and at the screen. | Removes the most obvious penny-price and capacity problems and gives the relative rules a broader cross-section than the original 56-name fixture. | It is not a point-in-time universe, does not include historical membership or delisted names, and does not independently verify every security type. |
| Impulse | Five sessions, at least 3 pre-move ATRs of net displacement, at least 0.60 closing-path efficiency, and persistent volume participation. | Separates a material, directional move from ordinary volatility, round-trip churn and a one-day volume spike. | It does not identify the economic cause of the move or establish statistical significance. |
| Consolidation | The pause immediately after the impulse lasts 2–5 sessions and must contract in true range, stay within ATR-scaled width and daily-range limits, retain at least half the move and avoid excessive extension. | Converts “a few consolidation days” into a short, bounded and quieter base. | It does not establish that the pattern has a causal or profitable edge. |
| Lean | Boundary proximity is measured in current ATR units; the latest signed close must move toward the same boundary. | Requires both location and recent movement, rather than calling a static price location a directional signal. | `CONTINUATION_WATCH` and `FAILURE_RISK` are heuristic review labels, not probabilities or trade instructions. |
| Timing | Generate the list at Thursday close; use the immediately following Friday only for evaluation. | Matches the PM's Thursday-night / Friday-morning workflow and creates a clear information barrier. | Daily bars cannot model exact Friday entry fills, intraday ordering, spread or market impact. |
| Outcome | Friday close beyond the continuation or failure boundary by 0.10 current ATR is a resolution; otherwise it is `STALLS`. Overnight and Friday-session returns are reported separately. | Tests whether the base actually resolves rather than using an arbitrary fixed percentage move. | It does not mean a close-to-close result was tradable from the intended entry. |

The 3-ATR, 0.60, 1.5x volume, 0.65 contraction, 0.25 boundary-distance and 0.10 outcome-buffer values are all initial hypotheses. They are kept in `config/rules.json`, exposed in output files and checked with one-at-a-time sensitivity runs. They were revised after inspecting earlier work, so the current version is not a clean holdout.

## How a bar history becomes a PM-list row

The screen has one fixed information boundary: the list is generated using data available through the `asof` close. For the requested workflow, `asof` is Thursday. Friday is never used to create or rank the list; it is used only by the backtest to evaluate what happened next.

The time layout for one candidate is:

```text
C[e-5] | e-4  e-3  e-2  e-1  e | e+1 ... t | t+1
       preceding close   5-session impulse   2-5-session base   Friday outcome only
```

For every ticker, the algorithm tries a five-session base first, then four, three and two sessions. If `p` is the proposed base length, the end of the impulse is `e = t-p`; the impulse is the five sessions ending at `e`, and the base is `e+1` through `t`. A candidate is accepted only if all of the following stages pass:

1. **Data and capacity eligibility.** The ticker has valid, contiguous OHLCV bars for the candidate, the endpoint prices are at least $5, and median dollar volume is at least $20m both before the impulse and at the screen date.
2. **Impulse.** The five-session close-to-close displacement is at least 3 pre-move ATRs, closing-path efficiency is at least 0.60, average volume is at least 1.5 times the preceding 60-session median, and at least three of five impulse days reach that volume baseline.
3. **Consolidation.** The proposed two-to-five-session base has lower mean true range than the impulse, bounded ATR-scaled width and daily range, at least half of the original displacement retained at its worst intraday extreme, and no extension beyond 1.25 times the original displacement.
4. **Lean.** First identify the direction of the five-session impulse. If it was UP, the base high is the continuation boundary and the base low is the failure boundary. If it was DOWN, the base low is the continuation boundary and the base high is the failure boundary. The row is labelled `CONTINUATION_WATCH` only when the close is within 0.25 current ATR of the continuation boundary and the latest signed close change moves toward it. It is labelled `FAILURE_RISK` when the close is within 0.25 current ATR of the failure boundary and the latest signed close change moves against the original direction. Otherwise it is `UNRESOLVED`.
5. **Output.** The row contains the event date, direction, base length, every threshold input, both raw and buffered boundaries, the lean and a human-readable reason string. If no base length passes, the ticker produces no row.

The production screen does **not** apply a hidden top-N cut, a post-hoc performance rank or the old 70/30 breakout score. `screen_asof` returns every ticker that passes the stages above. It sorts the display by lean, the exported continuation-boundary distance (`trend_distance_atr`) and ticker name; this is presentation only, and for a `FAILURE_RISK` row the relevant failure-boundary distance should be read from its separate field. The four names in `outputs/latest_screen.csv` are therefore the four qualifying rows on that as-of date, not four winners selected after looking at Friday returns. A PM who wants a fixed number of names or a portfolio-sizing rule would need to specify that as a separate, auditable policy.

The Friday evaluator then freezes the Thursday-known base boundaries and current ATR. A close beyond the continuation boundary by 0.10 ATR is `GOES_AGAIN`; a close beyond the failure boundary by the same buffer is `FAILS`; anything in between is `STALLS`. Overnight and Friday open-to-close movement are reported separately. These outcomes never flow back into the Thursday list.

The purpose of the construction stages is deliberately separated:

| Stage | Question it answers | If it fails |
|---|---|---|
| Eligibility | Is this name sufficiently priced and liquid for the prototype? | Do not interpret a relative-volume event as a tradable opportunity. |
| Impulse | Was the recent five-session move large and directional for this stock? | Reject ordinary movement and choppy round trips. |
| Participation | Did activity persist across the move? | Reject a move explained by one isolated volume spike. |
| Consolidation | Did the next 2–5 sessions become quieter and preserve the move? | Reject deep retracements, wide bases and continued expansion. |
| Lean | Is Thursday close near one edge and moving toward it? | Keep the valid setup as `UNRESOLVED` rather than inventing a direction. |
| PM output | What passed before Friday, and what should the reviewer inspect? | Emit no row if no candidate window passes; do not use Friday to rescue it. |

## Known issues and why they matter

The current version is suitable for a research take-home and a reviewable prototype. These limitations prevent a production or profitability claim:

- **Current-universe and survivorship bias.** The 448 names are manually selected today, not reconstructed as-of each historical date. Missing delisted names and historical constituents can make the backtest look cleaner than a true historical opportunity set.
- **Incomplete data coverage.** Seventeen requested names are unavailable or invalid in the current cache. The loader reports and skips them, but the sample is still not the agreed production universe. Yahoo public daily data also needs an explicit corporate-action and adjustment policy.
- **Only roughly two years of evidence.** The 104 Thursday/Friday pairs are materially better than the old 26-pair smoke window, but they do not cover every volatility and market regime. The 604 evaluated bases are also correlated: a ticker can appear repeatedly and names can share sector or market exposures.
- **Researcher-chosen thresholds.** V4 follows inspection of earlier versions. Sensitivity results show that sample counts change when the impulse or contraction cutoffs move. Without a frozen rule and later untouched period, performance comparisons can be affected by researcher degrees of freedom.
- **Attention is only a proxy.** Price and volume do not tell us whether attention came from news, a forced flow, a short squeeze or a broad investor audience. They also do not identify buyer/seller imbalance.
- **Daily-bar execution limits.** A Friday close can be caused by an overnight gap; daily OHLCV cannot establish the intraday ordering of both boundary touches or the exact fill, spread, impact, borrow and short availability.
- **Lean is not a calibrated forecast.** The labels are interpretable heuristics. The current continuation-watch group has a higher closing-resolution rate than the overall sample, but its mean direction-adjusted return is negative, so the evidence does not support a profitable signal claim.
- **The PM list has no portfolio policy yet.** The screen emits every qualifying row. It does not decide how many names to show, how to rank unresolved cases, how to size positions, or how to manage correlated exposures.

## Follow-up improvements and why

The improvements below should be done in this order because each addresses a different failure mode; expanding the universe alone does not solve them.

| Priority | Improvement | Why it matters | Evidence of completion |
|---|---|---|---|
| 1 | Freeze the current definition and evaluate a later untouched period. | Prevents continued threshold changes from being judged on the same history used to design them. | A versioned holdout report with no rule or universe changes after the freeze date. |
| 2 | Build a point-in-time 300–500-name universe with historical membership, delistings and an explicit ETF/security-type policy. | Removes the largest survivorship and selection biases and makes cross-sectional comparisons meaningful. | Universe snapshot by date, inclusion/exclusion reason and delisted-name audit. |
| 3 | Extend verified daily data to 5–10 years and split results by market regime. | Tests whether the pattern survives different volatility, rate and trend environments rather than one recent period. | Regime-level counts, confidence intervals and a missing-data report. |
| 4 | Verify corporate actions and adjustment policy with a second data source. | Split, dividend and symbol-history errors can create false impulses or false breaks. | Reconciliation checks and a documented adjusted/raw-price convention. |
| 5 | Add cluster-aware inference and block bootstrap by ticker and date. | The current observations are not independent; ordinary accuracy or p-values would overstate certainty. | Confidence intervals that respect repeated names, weeks and sector clustering. |
| 6 | Add a transaction-cost, spread, gap, borrow and fill model, preferably with intraday data for the Friday session. | A higher continuation rate is not useful if the move occurs before entry or is consumed by execution costs. | Net, cost-adjusted return distributions and a clearly specified entry timestamp. |
| 7 | Add timestamped news, search, options or social features as a separate attention test. | Directly tests the PM's “everyone is excited” wording instead of relying only on price-volume proxies. | Incremental out-of-sample comparison against the OHLCV-only baseline. |
| 8 | Agree a separate PM ranking and sizing policy. | The current screen identifies review candidates but does not decide how many positions or how to control correlated risk. | A documented top-N, exposure, stop/exit and position-sizing rule evaluated without changing the screen definition. |

The expected sequence is: first protect sample integrity and out-of-sample evaluation, then measure execution, and only afterward add richer attention data or a more complex model. Otherwise a more sophisticated model could simply fit the same biased sample more convincingly.

## Deliverables

| File | Purpose |
|---|---|
| `docs/definitions.md`, `config/rules.json` | Revised definitions and executable defaults |
| `src/screen.py`, `src/run_screen.py`, `src/data.py` | Features, screen and loading |
| `outputs/latest_screen.csv` | Candidate, every rule input, lean, boundary levels and reason |
| `src/backtest.py`, `outputs/backtest/` | Observations, lean summaries, coverage, impulse-only reference, sensitivity and manifest |
| `docs/evidence.md`, `docs/evidence_results.md` | Protocol, numbers and limitations |
| docs/researcher_thoughts.md | Personal research rationale, interview framing and submission posture |
| `docs/pm_note.md` | Eight-line PM note |
| `docs/alert_note.md` | Separate no-code early-gains alert proposal |
| `docs/revision_notes.md` | V4 changes and preserved history |
| `outputs/legacy_v1/`, `outputs/legacy_v2/`, `outputs/legacy_v3_26/` | Superseded results, clearly separated from V4 |
| `tests/test_rules.py` | Synthetic counterexamples, temporal isolation, outcome and data checks |

`manifest.json` records effective rules, runtime versions, loaded names, input hashes and source hashes. The manually curated universe has selection and survivorship bias; expanding from 56 to 448 improves breadth but does not make it point-in-time. The online refresh loaded 431 usable names; the remaining 17 are reported rather than silently imputed. Cached prices were not independently cross-checked in this revision and are not a point-in-time database. Daily bars cannot establish attention, fills, short availability or intraday path. V4 follows inspection of previous results and is not a clean holdout. The original brief budgets four hours; this repository includes subsequent revisions and does not claim they all occurred within that original budget.

AI was used to help revise definitions, implement and test code, and paraphrase explanations; the assumptions, outputs and limitations remain explicit for review.

## Researcher's perspective

The formal documents explain the executable definitions. [Researcher's perspective](docs/researcher_thoughts.md) explains the personal reasoning behind the main trade-offs: why the screen is rule-based, why attention is treated as a price-volume proxy, why `UNRESOLVED` and `FAILS` are kept visible, how I interpret the current evidence, and what I would do before making a production claim.
