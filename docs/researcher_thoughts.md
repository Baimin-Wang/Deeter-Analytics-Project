# Researcher's perspective

This note explains the reasoning behind the current version in my own words. The formal definitions describe what the code does; this note describes why I chose that design and where I think it is still incomplete.

## How I framed the problem

The PM brief is intentionally qualitative: find names that look unusually active, trade with volume, pause for a few days, and may continue on Friday. I did not want to pretend that daily OHLCV directly measures attention or sentiment. I treated price and volume as observable proxies and made that limitation explicit.

My first objective was not to find the best-performing threshold. It was to make the idea executable and auditable. A reviewer should be able to take one row, reconstruct the impulse and base, and understand why the row received its label without trusting a black-box score.

## The choices I made

I replaced the original fixed-percentage move with ATR-scaled displacement because a 6% move means different things for a low-volatility bank and a high-volatility technology stock. I added path efficiency because a large endpoint move can still be a round trip. I used volume across the whole five-session move rather than only at the endpoint because one isolated spike is weak evidence of persistent participation.

I defined consolidation as a short, quieter and bounded pause that retains the original move. The 2-5 session window is my operational reading of “a few”; it is not a natural law. The contraction, width, retention and extension checks each remove a different failure mode: continued expansion, a wide range, a deep retracement or a move that never really paused.

I separated the lean from the pattern definition. A stock can have a valid impulse and base but still be too far from either edge to justify a directional read. That is why the output includes `UNRESOLVED`. For the same reason, I did not turn the lean into a probability. The boundary-distance and latest-movement rule is a transparent heuristic, not a calibrated model.

I added `FAILS` as a diagnostic outcome even though the PM initially described only “goes again” and “stalls”. Treating an obvious reversal as a stall would hide whether the screen failed to find continuation or actively pointed toward the wrong side of the base. I still keep the PM-facing interpretation separate: `FAILS` is a diagnostic label, not a recommendation to trade the opposite direction.

## How I treated evidence

The Thursday-to-Friday timing is part of the research design. The list is generated from Thursday-close information, and Friday is used only for ex-post evaluation. This protects the screen from using the result it is supposed to predict.

I expanded the requested universe from 56 to 448 names and the evidence window from 26 to 104 Thursday/Friday pairs after identifying that the original sample was too narrow. That improves breadth and reduces dependence on a single short period, but it does not solve survivorship bias, missing delisted names or corporate-action uncertainty. I would rather state that limitation clearly than present the larger sample as production validation.

The current results are useful for judging the structure of the screen, not for claiming profitability. `CONTINUATION_WATCH` has a higher continuation rate than the all-setup baseline, and `FAILURE_RISK` has a much lower one, but the continuation-watch group's direction-adjusted mean return is still negative. My interpretation is that the labels may provide conditional ranking information while the trading edge remains unproven.

## What I would defend in an interview

- The rules are hypotheses translated from PM language, not requirements supplied by the PM and not optimized probabilities.
- ATR measures move size relative to the stock's own normal range; path efficiency measures whether the move was directional rather than choppy.
- Consolidation is not required to last five days. The code tests five, four, three and two sessions and keeps the longest qualifying window.
- A continuation boundary is the base edge in the original impulse direction; a failure boundary is the opposite edge. The lean requires both proximity and movement toward that edge.
- The PM list contains every row that passes the pre-Friday screen. There is no hidden top-N or Friday-performance selection.
- The current screen is a research prototype and review list, not an automated trading strategy.

## What I would do next

My next step would be to freeze the definition and evaluate a later untouched period on a point-in-time universe with delisted names. After that I would add cluster-aware confidence intervals, verify corporate-action handling, and model the actual Friday entry, spread, slippage, borrow and overnight gap. Only after those checks would I decide whether richer attention data or a learned ranking model adds value.

If the PM wants a fixed number of names or portfolio weights, I would add that as a separate policy layer. Keeping screen definition, evidence measurement and portfolio construction separate makes it easier to identify whether a problem comes from the pattern definition, the data or the trading implementation.

## Submission posture

I consider this version ready as a take-home research prototype because it is runnable, reproducible, explicit about assumptions and honest about negative evidence. I would not present it as a validated production signal. The most important follow-up is not another round of threshold tuning; it is a clean out-of-sample test with a historically correct universe and realistic execution assumptions.