# Evidence from the included run

The included run used 26 Thursday closes ending with the latest complete data available on 2026-09-21. It produced 49 ticker setups across 19 distinct Thursdays. The exact per-lean counts are in `outputs/backtest/summary.csv`; the raw observations are in `outputs/backtest/observations.csv`.

The observed rows were:

| Lean | Setups | Goes again | Stalls | Fails | Goes-again rate | Mean signed Friday return |
|---|---:|---:|---:|---:|---:|---:|
| CONTINUE_DOWN | 15 | 4 | 7 | 4 | 26.7% | -83.4 bps |
| CONTINUE_UP | 8 | 1 | 6 | 1 | 12.5% | -31.8 bps |
| STALL_RISK | 26 | 2 | 24 | 0 | 7.7% | +30.9 bps |

This is not evidence that the lean works. In this small sample, most setups stalled; both continuation labels had negative mean signed Friday returns, while the stall-risk group had a small positive average. The result is still useful: it demonstrates that the screen runs end-to-end, creates a modest number of candidates, and makes a falsifiable claim that can be improved with better definitions and data.

There are 26 Thursday dates in the requested window, but some have no setup or no usable following Friday because of holidays and the available data boundary. The summary file is authoritative for the exact number of distinct Thursdays represented in each lean group.

The main caveats are look-ahead in any future production data pipeline, survivorship from the fixed current universe, threshold selection without a clean holdout, multiple testing, and correlated names/weeks. No p-values are reported.
