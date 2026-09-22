# Definitions and research assumptions

This screen translates the PM's idea into a daily-price proxy for a salient move followed by a pause. "Excited" is interpreted as attention in either direction, consistent with a long/short book; a narrower interpretation would include only bullish enthusiasm. OHLCV does not measure attention, sentiment or investor positioning.

These are working definitions, not empirically justified optimal thresholds. Version 2 was revised after reviewing version 1 and its results; this is not an untouched holdout or a preregistered experiment. No parameter search was run for this revision.

## Universe and timing

Use the 56 current, manually selected US equities in `config/universe.csv`. This is a bounded prototype universe, not a claim to cover the PM's opportunity set. Universe size is not a quality target: confirm the PM's actual tradable names before expanding. The current list has selection and survivorship bias. A saved CSV snapshot is not a point-in-time constituent or unrevised historical database.

The screen uses information through the stated close. Run after Thursday for a Friday watchlist; a latest-close run on another weekday is explicitly a preview. Default CLI runs conservatively exclude the current UTC date, even if its US session has just finished. `--end` selects a historical cutoff; `--offline` uses only the supplied cache. Cross-sectional ranks use available names on the event date, and the rank denominator is exported. Missing or rejected tickers can change the ranks.

## Selection rules

Here `e` is the endpoint of a five-session price move, `t` is the screening close, and `C` is close. The endpoint is not necessarily a discrete news event or a one-day impulse.

| Phrase / constraint | Exact rule | Reason and limitation |
|---|---|---|
| Salient price move | `abs(C[e]/C[e-5]-1) >= 6%` and percentile rank of absolute return `>= 0.75` on e | 6% sets a visible absolute move floor; the percentile adds relative salience. Both are inherited working cutoffs, not evidence of attention or abnormality relative to each name's volatility. Rank uses average ties, so this is not exactly 25% of names. |
| With volume | Endpoint volume / median volume of the preceding 60 sessions `>= 1.30` | Tests activity 30% above its own baseline; the median limits influence from prior spikes. It does not test liquidity or sustained volume throughout the five-day move. Full 60-session history is required and e is excluded from its baseline. |
| A few days | Immediately following e, 2-5 observed trading sessions ending at t | Two gives more than a one-day pause; five limits the pause to roughly a trading week. These are scope choices, not inferred PM numbers. |
| Quiet daily closes | Maximum absolute close-to-close return across those sessions `<= 2%` | Bounds daily closing movement. Fixed percentages favor quieter names and can miss intraday turbulence. The first return starts at the endpoint close. |
| Bounded range | `max(high)/min(low)-1 <= 7%` across the pause | Caps the whole intraday envelope. It does not establish volatility contraction. |
| Limited displacement | `abs(C[t]/C[e]-1) <= 4%` | Keeps the endpoint and latest close reasonably near each other. This previously undocumented filter is retained; it does not guarantee that most of a 6% impulse survived. |
| Multiple eligible endpoints | Keep the longest qualifying pause | Deterministic tie rule, preserving the prior implementation. It is not the endpoint with the best future outcome. |

OHLC must be positive and internally consistent; volume must be nonnegative; nonfinite values and duplicate dates reject a symbol. A missing session cannot always be distinguished from a nontrading day without an exchange calendar. There is no new automatic liquidity cutoff. Prior-20-session median `close * volume` is disclosed for inspection, not treated as executable dollar liquidity.

## Lean: a shape read with an explicit directional interpretation

`position = (C[t] - pause_low) / (pause_high - pause_low)`. For an up move, `signed_position = position`; for a down move it is `1-position`. A zero-width range receives 0.5.

| Label | Rule | PM interpretation |
|---|---|---|
| TREND_SIDE | signed position >= 0.75 | Close lies in the quarter nearest the original trend's boundary: tentative continuation lean (up for UP; down for DOWN). |
| OPPOSITE_SIDE | signed position <= 0.25 | Close lies near the opposite boundary: original-trend continuation is vulnerable. This is not a validated reversal forecast. |
| MID_RANGE | 0.25 < signed position < 0.75 | No clear directional lean from price location alone; wait for resolution. |

Outer quarters give a simple distinction between edges and the middle. The 0.75/0.25 cutoffs are new interpretive choices, not fitted probabilities. The old 70/30 price-volume score is removed: volume alone has no direction and an additive score did not require volume confirmation. Latest volume divided by the preceding 20-session median remains a descriptive field; 20 sessions approximates a month. Low volume does not automatically invalidate a trend-side close.

Exported diagnostics are not extra filters:

- `range_contraction_ratio`: pause high-low percentage range / five-session move high-low percentage range. Below 1 indicates a narrower observed range, but windows differ in length and this is not a normalized volatility estimate.
- `impulse_retention`: `(C[t]-C[e-5])/(C[e]-C[e-5])`. One preserves the endpoint's price displacement, zero fully retraces it, and values above one extend it. Applies symmetrically to down moves.
- Actual endpoint return, volume ratio, rank and rank denominator, pause length, maximum daily absolute return, total range, endpoint drift, boundary prices, latest close, signed position and liquidity diagnostic are all in the CSV.

## Outcomes, separate from the lean

For each Thursday, evaluate only the immediately following calendar-day Friday. Skip missing Fridays or holidays; never substitute a later Friday. Let d be +1 for an up move and -1 for a down move.

- Primary signed return: `d * (Friday close / Thursday close - 1)`.
- GOES_AGAIN: signed return >= 2%; REVERSES: <= -2%; STALLS: strictly between -2% and +2%.
- The 2% boundary deliberately separates larger daily moves from small closing changes, but is not volatility-adjusted. REVERSES describes the original move's reversal, not whether every possible lean was wrong.
- Also report signed overnight (Thursday close to Friday open) and signed Friday intraday (open to close) returns, with the same 2% categories for intraday results.
- Report whether Friday touches beyond the original-trend boundary and whether it closes beyond it, using strict inequalities and the Thursday-known pause boundaries. These are alternative descriptions, not the primary 2% label. Touching says nothing about path order or fillability.

An overnight gap can create GOES_AGAIN even when Friday open-to-close is negative. Raw returns compound: `(1+overnight)*(1+intraday)-1 = close-to-close`; do not sum signed returns as an exact identity. No outcome is a net trading P&L, and opposite-direction returns are directional diagnostics rather than a borrow- and cost-adjusted short strategy.
