# Definitions: v4, a relative impulse followed by a contracting base

This version replaces the old absolute-return and endpoint-volume screen. It asks: **did a stock make a directional move large relative to its own normal daily range, with participation across the move, then pause in a smaller range while preserving the move?** Friday continuation means a closing resolution of that base in the original direction. The examples below are designed to show the intended behavior of each definition, not to imply that a passing example has predictive power.

"Everyone is excited" is interpreted as unusual price-and-volume activity, including bearish attention because the PM runs a long/short book. This is an explicit scope choice. It does not measure how many people are interested or whether sentiment is bullish. The alternative bullish-only interpretation is available by filtering `direction=UP`; actual attention requires timestamped news, search, social or options information.

`config/rules.json` is the executable parameter specification. Defaults below were chosen for their relation to the concept, not selected for Friday performance. V4 follows review of earlier results; it is not a blind holdout. A coherent definition still needs validation.

## What changed substantively

| Earlier rule | V4 replacement | Problem addressed |
|---|---|---|
| Five-day absolute return >= 6%, top quartile of 56 names | Net five-session displacement >= 3 times pre-move ATR, with path efficiency >= 0.60 | A move must be unusual relative to that stock's range and directional, not just large in percentage or relative to a small arbitrary pool. |
| Endpoint volume >= 1.3x | Whole-move mean volume >= 1.5x the pre-move median; at least three of five days at or above that median | Measures participation during the same period as the price move, not one possibly unrelated endpoint spike. |
| Relative volume presented as liquidity protection | Independent price and median dollar-volume eligibility rules | Relative activity cannot establish absolute liquidity. |
| Daily returns <= 2%, total range <= 7%, close drift <= 4% | Mean true-range contraction, ATR-scaled range/day caps, minimum worst-case retention and maximum extension | Requires an actual pause that becomes quieter and holds the move; slow retracement or continued trending is not automatically a base. |
| Price location alone determines lean | Distance to a base boundary in ATR units plus the latest signed price change | A directional watch requires both proximity and movement toward the relevant boundary. Volume is displayed, not assigned an inherently bullish/bearish sign. |
| Friday signed close-to-close return >= 2% | Friday close outside the Thursday-known base by 0.10 ATR | Tests resolution of the actual consolidation; fixed-percent returns can label moves that never clear the base. |
| One Friday return window | Separate base resolution, overnight gap, and Friday open-to-close movement | A pre-open gap is not a Friday-morning entry return. |

## Notation and information timing

Let `t` be the screening date, `e` a candidate end of the move, and `n=t-e` in observed sessions. Test n=2,3,4,5. The five impulse sessions are e-4 through e; `C0=C[e-5]` is the preceding close. Let `d=sign(C[e]-C0)` and `D=abs(C[e]-C0)`.

Daily true range is `TR[i]=max(H[i]-L[i], abs(H[i]-C[i-1]), abs(L[i]-C[i-1]))`, including gaps. `A0` is the arithmetic mean of 20 TRs ending at e-5, **before the entire impulse**. This is a simple moving ATR, not Wilder smoothing. The fixed pre-move baseline prevents the large move itself from inflating the hurdle. `At` is the corresponding 20-session mean through t, known when the list is produced; it scales Friday outcome buffers and distances in the lean.

The volume baseline `V0` is the median of 60 volumes ending at e-5. Twenty sessions approximate one trading month; 60 provide roughly a quarter of background volume without including the impulse. Full windows are required. Invalid, nonfinite or nonpositive baselines cannot qualify.

## End-to-end construction: impulse, base, lean and the PM list

The definition is a sequential pattern, not a collection of independent daily filters. Let `t` be the Thursday screen date. For a proposed base length `p` in `[5, 4, 3, 2]`, set `e=t-p`:

```text
C[e-5] | e-4 ... e | e+1 ... t | t+1
       | 5 impulse | p-session base | Friday outcome only
```

The five impulse sessions always end at `e`; the base begins on the next observed session and ends at `t`. The code tries `p=5` first, then `p=4`, `p=3` and `p=2`. This gives a deterministic longest-qualifying-window rule:

```text
for p in [5, 4, 3, 2]:
    e = t - p observed sessions
    test the five-session impulse ending at e
    test the p-session base from e+1 through t
    if every test passes:
        emit this candidate and stop
emit no candidate for this ticker/date
```

The length is therefore **not always five**. A two-day base is valid when it passes every contraction and retention condition; a five-day base is preferred only when it also passes. A one-day pause is outside this definition. A pause longer than five sessions is outside this short Friday setup rather than automatically being called a failure. The same search is used by the impulse-only reference, except that the base conditions are omitted; that reference is not the PM list.

The normal production call uses `require_base=True`. Thus every row in `outputs/latest_screen.csv` has passed both the impulse and base tests and has `is_base=true`. The backtest's impulse-only reference is an intentionally separate diagnostic path and must not be confused with the actionable screen.

The final PM list is simply the set of accepted rows at the chosen `asof` date. There is no implicit top-quartile or top-N filter, no Friday-performance ranking and no 70/30 score. The presentation order in the current code is `lean`, then the exported continuation-boundary distance (`trend_distance_atr`), then ticker; for `FAILURE_RISK`, the separate failure-boundary distance is the relevant field for review. The file keeps `UNRESOLVED` rows so the PM can see that the screen found a valid pattern but did not find a sufficiently directional boundary read. Any later decision to show only continuation watches, cap the number of names, or size positions would be a new explicit policy layered on top of this screen.

This separation matters for auditability:

- **Impulse** asks whether a recent five-session move is large and directional relative to the stock's own history.
- **Consolidation** asks whether the following two-to-five sessions become quieter, bounded and protective of that move.
- **Lean** asks whether Thursday's close is close enough to one boundary, and moving toward it, to justify a directional watch.
- **PM output** reports all rows that pass those tests; it does not pretend that the heuristic lean is a probability or a trade instruction.

No Friday field is available to any of these four steps. This is the information barrier that the temporal-isolation tests are intended to protect.

## 1. Eligible universe: liquidity is its own condition

The input is a named equity universe supplied via `--universe`. The default `config/universe.csv` contains 448 manually curated US-listed equity tickers across sectors. `config/universe_56.csv` preserves the original 56-name fixture. The cache currently has 431 usable expanded histories; 17 requested names are unavailable or invalid and are reported. The number of names is not a screen parameter. This version removes the cross-sectional percentile gate, so adding unrelated tickers does not change a valid name's salience threshold. Missing-session checks can still depend on the observed calendar. Offline runs skip names without usable cache files and report them; live runs can download them.

- Require endpoint close and screening close each >= **$5**, a working exclusion of penny-price names; it is not a guarantee against manipulation or bad data.
- Require median daily `close * volume` >= **$20 million** both in the 20 sessions ending before the impulse and in the 20 sessions preceding t. The median describes typical activity. The dollar floor is an explicit provisional capacity assumption, not a universal tradability test; larger intended orders may need a different universe.
- Only common equities belong in the input file. The supplied file is manually curated; the downloader does not infer security type or verify an ETF exclusion. A new input list must be checked before use.
- Reject malformed OHLCV and require the ticker to have every date observed in the loaded pool over the move and pause. This catches isolated missing bars, not exchange-wide missing data. No forward fill is used.

The move from 56 to 448 is a breadth improvement, not evidence that 448 is the correct production universe. It covers more sectors and reduces the chance that a small hand-picked list determines the result. It also adds more data failures, correlated names and selection choices. The actual live universe remains to be agreed. Current constituents, missing delistings and unverified corporate actions remain historical-data limitations; a larger current list does not fix them.

## 2. Salient directional impulse

Require both:

1. `D/A0 >= 3.0`. Over five sessions, the endpoint must move at least three normal daily true ranges. This sets a substantial displacement relative to the stock's own baseline. It is **not** a z-score or a significance threshold.
2. `D / sum(abs(C[i]-C[i-1]), i=e-4..e) >= 0.60`. At least 60% of the travelled closing-price distance becomes net displacement, reducing eligibility for round-trip churn. Zero total distance fails.

Five sessions define a recent trading-week move, not an asserted news event. The initial three-ATR and 60% cutoffs express magnitude and directional coherence separately. Earnings jumps can still pass; daily OHLCV cannot identify their cause.

## 3. With volume: participation across the move

Require `mean(V[e-4:e])/V0 >= 1.50`, and at least **3 of the 5** volumes >= V0. The first condition asks for average activity 50% above background; the second asks that ordinary-or-higher participation cover a majority of the move. It reduces, but does not eliminate, domination by a single spike. It does not infer buyer/seller imbalance, institutional interest or available execution depth.

The complete five-session volume measure replaces endpoint-only confirmation. Both the ratio and active-session count are exported.

## 4. A few consolidation days: contraction with retention

Require 2-5 sessions immediately after e. Two provides more than a one-day interruption; five keeps the pause within roughly a trading week. These bounds remain because the earlier concern was the meaning of consolidation, not a requirement to change every number.

Let `B_low=min(L[e+1:t])`, `B_high=max(H[e+1:t])`. Require **all** of:

| Condition | Default | Why |
|---|---:|---|
| Mean pause TR / mean impulse TR | <= 0.65 | At least a 35% reduction in mean daily range. Averages compare daily activity despite different window lengths. |
| `(B_high-B_low)/A0` | <= 1.50 | The entire base fits within 1.5 pre-move normal daily ranges; contraction alone could accept a still-wide base after an enormous impulse. |
| Maximum pause-day TR / A0 | <= 1.50 | Rejects a large gap or turbulent day that a calm closing return could hide. |
| Worst intraday retained displacement / D | >= 0.50 | At every observed pause extreme, at least half the net original move survives. A quiet but deep retracement fails. |
| Furthest intraday displacement / D | <= 1.25 | Permit at most another quarter of the original move beyond its endpoint; a continued trend should not be relabelled a pause. |

For up moves, worst retention is `(B_low-C0)/D` and furthest displacement is `(B_high-C0)/D`. For down moves they are `(C0-B_high)/D` and `(C0-B_low)/D`. Also export close retention `d*(C[t]-C0)/D`, though it is not an additional filter.

These are structural definitions, not proof of a technical pattern's edge. If multiple endpoints qualify, keep the **longest qualifying pause**: it has the most observed consolidation history. This deterministic tie rule does not use Friday results. Record the endpoint so a reviewer can reconstruct the choice.

## 5. Lean: an inspectable conditional read

The original trend means the direction of the five-session impulse, not a long-term market trend. Name the base edges explicitly:

| Impulse direction | Continuation boundary | Failure boundary |
|---|---|---|
| UP | `B_high` | `B_low` |
| DOWN | `B_low` | `B_high` |

The continuation boundary is the edge that would be broken if the original impulse resumed. The failure boundary is the opposite edge; breaking it means the base has resolved against the original impulse. Distances are measured from `C[t]` in units of `At`. The implementation field `trend_distance_atr` means distance to the continuation boundary, while `failure_distance_atr` means distance to the failure boundary. `last_signed_change=d*(C[t]-C[t-1])/At`, so a move in the original impulse direction is positive and a move against it is negative.

| Lean | Exact condition | Meaning |
|---|---|---|
| CONTINUATION_WATCH | Distance to continuation boundary <= **0.25 At** AND `last_signed_change > 0` | The stock is within a quarter normal daily range of the edge that would resume the original UP/DOWN impulse, and its latest close moved toward that edge. |
| FAILURE_RISK | Distance to failure boundary <= **0.25 At** AND `last_signed_change < 0` | The stock is within a quarter normal daily range of the opposite edge, and its latest close moved against the original impulse toward that edge. |
| UNRESOLVED | Neither condition | No sufficiently clear directional read; an unchanged close also lands here. |

The quarter-ATR distance makes proximity comparable across different base widths. The sign requirement prevents calling proximity alone directional confirmation. This remains a weak, untrained heuristic, not an estimated probability. A narrow base may lie within a quarter ATR of both sides; the mutually exclusive sign conditions determine the read. Latest relative volume and pause/impulse volume ratio are descriptive: a quiet pause is not automatically penalized, and volume has no unconditional direction.

The output includes the exact distances, latest signed move, original direction, both raw boundaries and both buffered Friday levels. Reasons state the observed condition, not confidence in a predicted outcome.

## Concrete positive and negative examples

The examples below are synthetic unit-test cases. They explain why a row passes or fails the rule; they do **not** show that the rule makes money. The tests in `tests/test_rules.py` construct the same types of cases and assert the expected behavior.

| Rule | Positive case | Negative case | What the test demonstrates |
|---|---|---|---|
| Price and typical liquidity | Price is $50 and the prior 20-session median dollar volume is $30m, both above the $5 / $20m eligibility floors. | Price is $4.50 or median dollar volume is $10m, even if relative volume doubles. | Relative activity cannot rescue a penny-price or capacity problem. |
| Relative directional impulse | Pre-move `A0=$1.20`, five-session displacement `D=$4.00`: `D/A0=3.33`; closing path travelled $5, so efficiency is 0.80. | `D=$1.80`, `A0=$1.20`: 1.50 ATR; or a path that travels $10 before ending $4 away: efficiency 0.40. | A move must be large for that name and mostly directional. The second case rejects churn that an endpoint return alone would accept. |
| Participation | Background volume `V0=1m`; impulse volumes `[1.4,1.6,1.8,1.2,1.5]m`: mean 1.50x and 5/5 active sessions. | `[0.8,0.8,0.8,0.8,4.5]m`: one large spike but mean 1.34x and only 1/5 active sessions. | The move must have broad participation; one event-day spike is insufficient. |
| Base contraction | Mean impulse TR is 2.0, mean pause TR is 1.1, so ratio 0.55; pause width is 1.2 `A0`, worst retention 0.75, extension 1.10. | Pause TR ratio 0.80, or a quiet retracement whose worst retention is 0.30, or extension 1.50. | A base is quieter, bounded and still holds the move. Slow drift and continued trend do not pass merely because closes are small. |
| Continuation lean | Up base upper boundary $105, current ATR $1, close $104.80, last signed close change +$0.10: trend distance 0.20 ATR and movement is toward the boundary. | Close is equally near the upper edge but last change is -$0.10: the location alone does not create a continuation read. | The lean needs both proximity and current movement; it is not a price-position probability. |
| Failure lean | Down base lower boundary $95 and upper boundary $100, current ATR $1, close $99.80, raw last close change +$0.10 (signed change -$0.10): failure distance 0.20 ATR and movement is toward the upper failure boundary. | Close is near the failure boundary but unchanged, or moving back into the base. | The rule distinguishes a developing failure risk from a static boundary location. |
| Friday outcome | Up base high $105, Thursday ATR $2, buffer $0.20: Friday close $105.30 is `GOES_AGAIN`. | Close $105.20 exactly at the buffered level is `STALLS`; close $99.70 below the lower buffered level is `FAILS`. | Outcomes refer to confirmed closing resolution, with equality treated conservatively. |
| Gap versus session | Thursday close $100, Friday open $106, Friday close $105.30: base resolution is upward, but Friday open-to-close is negative. | A Friday close inside the base can still have a large intraday excursion. | Overnight continuation and Friday-session continuation are separate facts. |

These cases are effective as implementation checks because each changes one conceptual property at a time: size relative to baseline, path direction, participation breadth, contraction, retention, boundary proximity or session timing. They are not a substitute for a long historical sample. A passing synthetic case proves the code implements the stated rule; it cannot prove the PM's economic hypothesis.

## 6. Goes again versus stalls: resolution of the base

Use the immediately following calendar-day Friday only; skip a holiday or missing bar. Freeze B_low, B_high and At at Thursday close. Buffer `b=0.10*At` requires a positive margin beyond the boundary rather than any arbitrarily small cross; 0.10 is an initial noise allowance, not a calibrated optimal level or a tick-size model.

- For an UP impulse: GOES_AGAIN if Friday close > B_high+b; FAILS if Friday close < B_low-b.
- For a DOWN impulse: GOES_AGAIN if Friday close < B_low-b; FAILS if Friday close > B_high+b.
- Otherwise STALLS: **no confirmed closing resolution**. Exact equality with a buffered boundary remains STALLS.

FAILS is a diagnostic subclass of non-continuation. It describes failure of the original base, not automatic failure of the lean. STALLS does not mean zero intraday volatility: it includes rejected intraday breaks that return inside the buffered range. Report touches of each buffered boundary and whether both were touched; daily data does not establish ordering.

This closing-resolution target can count an overnight gap as GOES_AGAIN. Therefore also export raw and direction-adjusted overnight, open-to-close, and close-to-close returns. A separate Friday-session label uses `d*(Friday close-Friday open)/At`: >= **0.50** is INTRADAY_WITH_TREND, <= **-0.50** is INTRADAY_AGAINST_TREND, otherwise SMALL_MOVE. Half a known normal daily range defines a material session move for this diagnostic; it is not the base-resolution label and does not make open-to-close a net tradable return.

For example, an up-base upper edge of 102 and At=2 gives a continuation close level of 102.2. Friday open=104 and close=103 resolves upward, but the session move is -0.5 At: INTRADAY_AGAINST_TREND. The output must show both facts.

## Evidence and remaining choices

Report base-resolution counts, raw sample sizes, distinct Thursdays, all-setup and always-stall baselines, lean/direction splits, and Friday-session movement separately. The default evidence window is 104 completed Thursday/Friday pairs, roughly two years; 26 pairs is retained only as a fast smoke check. A longer window reduces dependence on one regime but does not fix survivorship or selection bias. Also report salient high-volume impulses without the consolidation filters, using the same 2-5-session age search and longest-qualifying tie rule, one name per Thursday. Removing the base conditions can select a different endpoint or direction. Its subsequent high-low window can be wider, making its boundary-resolution rates mechanically different; compare return distributions too. This is a descriptive, overlapping reference, not a matched control or proof that consolidation adds predictive value.

Use a small disclosed one-at-a-time sensitivity check on the impulse and contraction cutoffs, with no best-variant selection. Keep the default result even if it is sparse or unfavorable. Entry rules, output fields, reason strings and outcome labels must use this same definition. Future work is an untouched-period evaluation on an agreed universe; point-in-time membership and corporate-action checks must precede production claims.
