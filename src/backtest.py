"""V4 evidence: base resolution, Friday session returns and disclosed reference samples."""
from __future__ import annotations
import argparse
import hashlib
import json
import platform
from pathlib import Path
import pandas as pd
import numpy as np
from .data import load_universe
from .screen import build_features, friday_outcome, screen_asof, load_rules, DEFAULT_RULES_PATH, SCREEN_COLUMNS, OUTCOME_COLUMNS


def summarize(result, split=True, baseline_name='ALL_SETUPS'):
    rows = []
    groups = [(baseline_name, result)]
    if split and not result.empty:
        groups += [(str(k), v) for k, v in result.groupby('lean')]
        groups += [(f'{k[0]} / {k[1]}', v) for k, v in result.groupby(['lean', 'direction'])]
    for name, group in groups:
        size = len(group)
        row = dict(group=name, observations=size, weeks=group['asof'].nunique() if size else 0)
        for label in ['GOES_AGAIN', 'STALLS', 'FAILS']:
            row[label.lower()] = int(group['outcome'].eq(label).sum()) if size else 0
        for metric, count in [('goes_again_rate', 'goes_again'), ('failure_rate', 'fails'), ('always_stall_accuracy', 'stalls')]:
            row[metric] = row[count] / size if size else np.nan
        row['resolved_either_way_rate'] = (row['goes_again'] + row['fails']) / size if size else np.nan
        for col in ['signed_return', 'signed_overnight_return', 'signed_intraday_return']:
            row[f'mean_{col}_bps'] = group[col].mean() * 10000 if size else np.nan
        row['median_signed_return_bps'] = group['signed_return'].median() * 10000 if size else np.nan
        row['intraday_with_trend_rate'] = group['intraday_outcome'].eq('INTRADAY_WITH_TREND').mean() if size else np.nan
        row['intraday_against_trend_rate'] = group['intraday_outcome'].eq('INTRADAY_AGAINST_TREND').mean() if size else np.nan
        row['touch_breakout_rate'] = group['touched_beyond_trend_boundary'].mean() if size else np.nan
        row['both_sides_touched_rate'] = group['both_sides_touched'].mean() if size else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def thursday_dates(last, weeks):
    cutoff = pd.Timestamp(last) - pd.Timedelta(days=1)
    anchor = cutoff - pd.Timedelta(days=(cutoff.dayofweek - 3) % 7)
    return pd.date_range(end=anchor, periods=weeks, freq='W-THU')


def evaluate(features, dates, rules, require_base=True):
    rows, coverage = [], []
    for asof in dates:
        setups = screen_asof(features, asof, rules, require_base=require_base)
        evaluated = 0
        for row in setups.to_dict('records'):
            outcome = friday_outcome(features[row['ticker']], row, rules)
            if outcome:
                rows.append({**row, **outcome})
                evaluated += 1
        coverage.append(dict(asof=str(asof.date()), available_symbols=sum(asof in f.index for f in features.values()),
                             setups=len(setups), evaluated=evaluated, missing_friday=len(setups)-evaluated))
    return pd.DataFrame(rows, columns=SCREEN_COLUMNS + OUTCOME_COLUMNS), pd.DataFrame(coverage)


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument('--weeks', type=int, default=104,
                        help='Number of completed Thursday/Friday pairs; default is 104 (~2 years)')
    parser.add_argument('--output-dir', default='outputs/backtest')
    parser.add_argument('--symbols', nargs='*', default=None)
    parser.add_argument('--universe', default=str(root / 'config/universe.csv'))
    parser.add_argument('--rules', default=str(DEFAULT_RULES_PATH))
    parser.add_argument('--end', default=None)
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--sensitivity', action='store_true', help='Report four predeclared one-at-a-time variants; never select a winner')
    args = parser.parse_args()
    if args.weeks <= 0:
        parser.error('--weeks must be positive')
    rules = load_rules(args.rules)
    end = pd.Timestamp(args.end) if args.end else pd.Timestamp.utcnow().tz_localize(None).normalize()-pd.Timedelta(days=1)
    start = end-pd.Timedelta(days=max(520, args.weeks*7+150))
    data = load_universe(Path(args.universe), str(start.date()), str(end.date()), symbols=args.symbols, offline=args.offline)
    features = build_features(data, rules)
    last = max(f.index.max() for f in features.values())
    dates = thursday_dates(last, args.weeks)
    result, coverage = evaluate(features, dates, rules)
    controls, control_coverage = evaluate(features, dates, rules, require_base=False)
    summary = summarize(result)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    for name, table in [('observations', result), ('summary', summary), ('coverage', coverage),
                        ('impulse_only_observations', controls), ('impulse_only_coverage', control_coverage),
                        ('impulse_only_summary', summarize(controls, split=False, baseline_name='IMPULSE_ONLY'))]:
        table.to_csv(outdir / f'{name}.csv', index=False)
    variants = [('default', {})]
    if args.sensitivity:
        variants += [('impulse_atr_2.5', {'min_impulse_atr': 2.5}),
                     ('impulse_atr_3.5', {'min_impulse_atr': 3.5}),
                     ('contraction_0.50', {'max_tr_contraction': .50}),
                     ('contraction_0.80', {'max_tr_contraction': .80})]
    sensitivity = []
    for name, change in variants:
        variant_result = result if not change else evaluate(features, dates, {**rules, **change})[0]
        sensitivity.append(dict(variant=name, changes=json.dumps(change, sort_keys=True), **summarize(variant_result, split=False).iloc[0].to_dict()))
    pd.DataFrame(sensitivity).to_csv(outdir / 'sensitivity.csv', index=False)
    manifest = dict(rule_version=rules['version'], rules=rules, universe_path=str(Path(args.universe).resolve()),
                    requested_universe_size=len(pd.read_csv(args.universe)), loaded_universe_size=len(data),
                    requested_end=str(end.date()), latest_data=str(last.date()),
                    runtime=dict(python=platform.python_version(), pandas=pd.__version__, numpy=np.__version__),
                    weeks=args.weeks, offline=args.offline, sensitivity=args.sensitivity, loaded_symbols=list(data),
                    data_sha256={t: hashlib.sha256(f.to_csv().encode()).hexdigest() for t,f in data.items()},
                    universe_sha256=hashlib.sha256(Path(args.universe).read_bytes()).hexdigest(),
                    source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'src/screen.py',root/'src/backtest.py',root/'src/data.py']})
    (outdir/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Thursdays: {len(dates)} | base observations: {len(result)} | impulse-only: {len(controls)}')
    print(summary.to_string(index=False))
    print(pd.DataFrame(sensitivity)[['variant','observations','goes_again','stalls','fails']].to_string(index=False))
    print(f'Wrote {outdir}')


if __name__ == '__main__':
    main()
