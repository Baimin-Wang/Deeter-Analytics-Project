# Evidence from the supplied v4 run

The online refresh requested all 448 names in `config/universe.csv`. It loaded 431 usable histories; 15 tickers returned no usable history and two downloaded files contained only one row, so the loader rejected 17 names and did not impute them. The run covers 104 Thursday/Friday pairs from 2024-09-26 through 2026-09-17. This is roughly two years, rather than the old 26-pair, six-month smoke window. There were 618 qualifying bases before Friday evaluation, 604 usable Friday observations, 16 Thursdays with no setup, and 14 setups whose following Friday was a holiday or missing bar.

The primary outcome is a close outside the Thursday-known base plus a 0.10-ATR buffer. It is not the old fixed 2% label, so earlier counts cannot be pooled with this table.

| Lean | Observations | Thursdays | Goes again | Stalls | Fails | Goes-again rate | Mean signed close-to-close | Mean signed overnight | Mean signed Friday session |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| All bases | 604 | 85 | 81 | 432 | 91 | 13.4% | -17.7 bps | -2.5 bps | -15.2 bps |
| Continuation watch | 143 | 54 | 36 | 98 | 9 | 25.2% | -55.5 bps | -6.8 bps | -48.5 bps |
| Failure risk | 135 | 52 | 2 | 92 | 41 | 1.5% | -0.2 bps | +2.4 bps | -2.3 bps |
| Unresolved | 326 | 79 | 43 | 242 | 41 | 13.2% | -8.3 bps | -2.6 bps | -5.9 bps |

The continuation-watch group crossed its continuation boundary 36 times, but its average direction-adjusted close-to-close return was -55.5 bps and its Friday-session return was -48.5 bps. That is not evidence of a profitable continuation signal. The failure-risk group rarely closed through its failure boundary, but that is a statement about this label and target, not proof that it should be traded in the opposite direction. The groups remain correlated and were defined after inspecting earlier work. The continuation boundary is the base high after an UP impulse and the base low after a DOWN impulse; the failure boundary is the opposite edge.

Always calling the result STALLS would match 432/604 observations (71.5%). The larger sample makes the counts more stable than the earlier six-month result, but it still does not create independent observations: names, sectors, and market weeks overlap. The 104-pair window also spans multiple regimes without claiming to cover every cycle.

Friday session and overnight behavior remain different. For all bases, the mean signed overnight move was -2.5 bps while the mean signed Friday open-to-close move was -15.2 bps. A closing GOES_AGAIN can therefore be caused by an overnight gap even if the Friday session gives back part of it. The raw file keeps all three return windows and boundary touches.

## Reference without base filters

The impulse-only reference has 2,653 observations on 93 Thursdays: 205 closing continuations, 2,166 stalls and 282 failures. Its mean signed close-to-close return is -37.7 bps and mean signed Friday-session return is -35.7 bps. It uses the same eligibility, directional impulse, participation and 2-5-session age search but omits base contraction, width, retention and extension filters. Because that can select a different endpoint and a different boundary window, it is an overlapping descriptive reference rather than a matched causal control.

## Disclosed sensitivity

| One-at-a-time variant | Observations | Goes again | Stalls | Fails |
|---|---:|---:|---:|---:|
| Default: impulse >= 3.0 ATR; contraction <= 0.65 | 604 | 81 | 432 | 91 |
| Impulse >= 2.5 ATR | 694 | 90 | 501 | 103 |
| Impulse >= 3.5 ATR | 499 | 66 | 356 | 77 |
| Contraction <= 0.50 | 352 | 41 | 258 | 53 |
| Contraction <= 0.80 | 684 | 92 | 487 | 105 |

Every variant is reported; none is selected because it has a better Friday result. The sample changes materially with the contraction cutoff, which is evidence that this is still a research definition rather than a calibrated production signal.

## Latest-close preview

The expanded latest-close run on 2026-09-21 produces four names:

These are all four qualifying rows returned by the screen at that as-of date. The runner does not apply a hidden top-N or Friday-performance ranking; it orders rows for review by lean and the exported continuation-boundary distance (`trend_distance_atr`). For `FAILURE_RISK`, review the separate failure-boundary distance. Because 2026-09-21 is a Monday, this is a latest-close preview rather than the requested Thursday-night list.

- JBHT: DOWN / FAILURE_RISK. The two-day base is 0.44x the impulse true range, retains 97% of the move, and the close is 0.17 current ATR from the failure boundary.
- BAC: DOWN / UNRESOLVED. The three-day base is 0.46x the impulse true range and retains 87%, but the close is about 0.43 ATR from both edges.
- HWM: DOWN / UNRESOLVED. The five-day base is 0.53x the impulse true range, with 2.48x mean impulse volume and 84% worst retention; the latest close moved slightly toward the trend side but is not within the boundary threshold.
- KIM: DOWN / UNRESOLVED. The three-day base is 0.44x the impulse true range, with 1.75x mean impulse volume and 86% worst retention; the latest signed move is nearly flat.

These are Monday previews, not a Thursday-night list. The levels are descriptive watch boundaries, not trade instructions.

The run demonstrates the practical value of the longer window and broader pool: 604 evaluated bases instead of 19 in the 56-name, 26-pair run. It does not prove that the expanded names are point-in-time constituents, that the current universe is unbiased, or that the lean predicts Friday. The next step is to freeze this version, agree the PM's actual universe, and evaluate a later untouched period with historical membership and verified corporate-action data.
