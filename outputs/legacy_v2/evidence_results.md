# Evidence from the supplied v2 run

The offline run ends at 2026-09-21 and covers 26 Thursday dates, 2026-03-26 through 2026-09-17, in the fixed 56-name universe. There were 55 qualifying ticker setups, of which five had no next-day Friday bar and were excluded from outcomes. The remaining 50 observations span 19 distinct Thursdays. Five Thursday dates had no setup. See `coverage.csv` for the full accounting.

| Shape read | Setups | Goes again | Stalls | Reverses | Goes-again rate | Mean signed close-to-close | Mean signed overnight | Mean signed Friday intraday |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| All setups | 50 | 7 | 38 | 5 | 14.0% | -10.6 bps | +2.4 bps | -12.5 bps |
| Trend side | 14 | 3 | 8 | 3 | 21.4% | -49.1 bps | +11.5 bps | -58.7 bps |
| Middle | 22 | 3 | 17 | 2 | 13.6% | -24.0 bps | -12.2 bps | -11.7 bps |
| Opposite side | 14 | 1 | 13 | 0 | 7.1% | +48.9 bps | +16.4 bps | +32.7 bps |

All signed returns are oriented to the original five-session move. These are unweighted descriptive returns, not portfolio or net execution P&L. Overnight and intraday simple returns compound and their means need not sum exactly to the close-to-close mean.

Trend-side names had more moves beyond 2% in either direction: 42.9%, versus 24.0% for all setups. Their continuation and reversal counts were equal, and their mean signed return was negative. This does not validate a continuation forecast. The apparent distinction may be about movement magnitude; with 14 trend-side observations on only eight Thursdays, it is too small and dependent a sample to establish even that interpretation.

Always predicting STALLS would be correct in 38/50 cases (76%). Thus a high stall accuracy alone would be uninformative. Only 4/50 observations continued by at least 2% from Friday open to close, versus 7/50 measured from Thursday close. Six of 14 trend-side names closed beyond the pause's trend boundary, whereas only three met the primary +2% threshold: range breakout and a large closing return are different targets. The full summary also splits each shape by original direction; aggregate rates can hide this mix.

The latest-close preview for Monday 2026-09-21 has five names: TMO is UP / TREND_SIDE; BAC is DOWN / MID_RANGE; GE, MS and GS are DOWN / OPPOSITE_SIDE. This is not a historical Thursday-night list, and the lean is a shape read rather than a calibrated probability.

The v1 artifacts remain in `outputs/legacy_v1`. V2 has 50 evaluated setups versus v1's 49: META on 2026-04-16 is added after excluding the endpoint from the historical volume baseline; no old ticker/date observation is removed. Lean definitions have also changed, so group results are not directly comparable. This revision used the supplied cache without a fresh independent price-source check and was made after inspecting v1 results. It is neither an out-of-sample success claim nor evidence that these thresholds are optimal.
