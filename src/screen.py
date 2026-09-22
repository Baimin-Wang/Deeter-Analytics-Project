"""V4: relative directional impulse, broad participation, then a contracting base."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

DEFAULT_RULES_PATH = Path(__file__).resolve().parents[1] / 'config/rules.json'


def load_rules(path=DEFAULT_RULES_PATH):
    rules = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    numeric = {k: v for k, v in rules.items() if k != 'version'}
    if any(not isinstance(v, (int, float)) or not np.isfinite(v) or v <= 0 for v in numeric.values()):
        raise ValueError('Rule parameters must be positive finite numbers')
    if rules['min_pause_sessions'] > rules['max_pause_sessions']:
        raise ValueError('Pause bounds are reversed')
    if rules['min_active_sessions'] > rules['impulse_sessions']:
        raise ValueError('Active sessions exceed impulse sessions')
    return rules


RULES = load_rules()
SCREEN_COLUMNS = [
    'ticker', 'asof', 'event_date', 'direction', 'lean', 'is_base',
    'impulse_return_5d', 'impulse_atr', 'path_efficiency', 'pre_impulse_atr', 'asof_atr',
    'impulse_volume_ratio', 'active_impulse_sessions', 'pre_impulse_volume_median',
    'pre_impulse_dollar_volume', 'median_dollar_volume_20', 'event_close', 'asof_close',
    'consolidation_days', 'tr_contraction_ratio', 'pause_width_atr', 'max_pause_daily_tr_atr',
    'worst_retention', 'furthest_displacement', 'close_retention',
    'consolidation_low', 'consolidation_high', 'trend_distance_atr', 'failure_distance_atr',
    'last_signed_change_atr', 'recent_volume_ratio', 'pause_to_impulse_volume_ratio',
    'continuation_level', 'failure_level', 'reason',
]
OUTCOME_COLUMNS = [
    'friday', 'friday_return', 'signed_return', 'outcome', 'overnight_return',
    'signed_overnight_return', 'intraday_return', 'signed_intraday_return',
    'intraday_move_atr', 'intraday_outcome', 'closed_beyond_trend_boundary',
    'touched_beyond_trend_boundary', 'touched_beyond_failure_boundary', 'both_sides_touched',
]


def _feature_frame(frame, rules=None):
    r = RULES if rules is None else rules
    out = frame.copy().sort_index()
    previous = out['close'].shift(1)
    out['tr'] = pd.concat([out['high'] - out['low'], (out['high'] - previous).abs(),
                           (out['low'] - previous).abs()], axis=1).max(axis=1)
    out.loc[previous.isna(), 'tr'] = np.nan
    n = r['impulse_sessions']
    out['atr'] = out['tr'].rolling(r['atr_sessions']).mean()
    out['pre_impulse_atr'] = out['atr'].shift(n)
    out['pre_impulse_volume_median'] = out['volume'].rolling(r['volume_baseline_sessions']).median().shift(n)
    dollars = out['close'] * out['volume']
    out['pre_impulse_dollar_volume'] = dollars.rolling(r['liquidity_sessions']).median().shift(n)
    out['median_dollar_volume_20'] = dollars.shift(1).rolling(r['liquidity_sessions']).median()
    vol20 = out['volume'].shift(1).rolling(r['liquidity_sessions']).median()
    out['recent_volume_ratio'] = out['volume'] / vol20.replace(0, np.nan)
    return out


def build_features(data, rules=None):
    return {t: _feature_frame(f, rules) for t, f in data.items()}


def lean_from_conditions(trend_distance, failure_distance, signed_change, rules=None):
    r = RULES if rules is None else rules
    limit = r['lean_boundary_distance_atr']
    if trend_distance <= limit and signed_change > 0:
        return 'CONTINUATION_WATCH'
    if failure_distance <= limit and signed_change < 0:
        return 'FAILURE_RISK'
    return 'UNRESOLVED'


def _candidate_for_date(ticker, frame, asof, rules=None, require_base=True, calendar=None):
    r = RULES if rules is None else rules
    if asof not in frame.index:
        return None
    pos = frame.index.get_loc(asof)
    n = r['impulse_sessions']
    if not isinstance(pos, (int, np.integer)):
        return None
    latest = frame.iloc[pos]
    if latest['close'] < r['min_price'] or not np.isfinite(latest['atr']) or latest['atr'] <= 0:
        return None
    if not np.isfinite(latest['median_dollar_volume_20']) or latest['median_dollar_volume_20'] < r['min_median_dollar_volume']:
        return None
    for days in range(r['max_pause_sessions'], r['min_pause_sessions'] - 1, -1):
        ep = pos - days
        if ep < r['volume_baseline_sessions'] + n - 1:
            continue
        e = frame.iloc[ep]
        event_date = frame.index[ep]
        if calendar is not None:
            observed = calendar[(calendar >= frame.index[ep-n]) & (calendar <= asof)]
            if not observed.equals(frame.index[ep-n:pos+1]):
                continue
        atr0, v0 = float(e['pre_impulse_atr']), float(e['pre_impulse_volume_median'])
        if not np.isfinite([atr0, v0, e['pre_impulse_dollar_volume']]).all() or atr0 <= 0 or v0 <= 0:
            continue
        if e['close'] < r['min_price'] or e['pre_impulse_dollar_volume'] < r['min_median_dollar_volume']:
            continue
        start = float(frame.iloc[ep-n]['close'])
        delta = float(e['close'] - start)
        displacement = abs(delta)
        if displacement / atr0 < r['min_impulse_atr']:
            continue
        sign = 1 if delta > 0 else -1
        move = frame.iloc[ep-n+1:ep+1]
        travelled = frame['close'].iloc[ep-n:ep+1].diff().abs().sum()
        efficiency = displacement / travelled if travelled > 0 else 0
        volume_ratio = float(move['volume'].mean() / v0)
        active = int(move['volume'].ge(v0).sum())
        if efficiency < r['min_path_efficiency'] or volume_ratio < r['min_impulse_volume_ratio'] or active < r['min_active_sessions']:
            continue
        pause = frame.iloc[ep+1:pos+1]
        low, high = float(pause['low'].min()), float(pause['high'].max())
        atr = float(latest['atr'])
        close = float(latest['close'])
        contraction = float(pause['tr'].mean() / move['tr'].mean())
        width_atr = (high - low) / atr0
        max_tr_atr = float(pause['tr'].max() / atr0)
        worst = (low-start) / displacement if sign == 1 else (start-high) / displacement
        furthest = (high-start) / displacement if sign == 1 else (start-low) / displacement
        is_base = bool(contraction <= r['max_tr_contraction'] and width_atr <= r['max_pause_width_atr']
                       and max_tr_atr <= r['max_pause_daily_tr_atr'] and worst >= r['min_worst_retention']
                       and furthest <= 1 + r['max_extension_fraction'])
        if require_base and not is_base:
            continue
        trend_distance = (high-close) / atr if sign == 1 else (close-low) / atr
        failure_distance = (close-low) / atr if sign == 1 else (high-close) / atr
        signed_change = float(sign * (close - frame.iloc[pos-1]['close']) / atr)
        lean = lean_from_conditions(trend_distance, failure_distance, signed_change, r) if require_base else 'IMPULSE_ONLY'
        buffer = r['outcome_buffer_atr'] * atr
        continuation_level = high + buffer if sign == 1 else low - buffer
        failure_level = low - buffer if sign == 1 else high + buffer
        direction = 'UP' if sign == 1 else 'DOWN'
        reason = (f"{direction} {displacement/atr0:.2f} ATR move; mean volume {volume_ratio:.2f}x, "
                  f"{active}/{n} days >= baseline; {days}d pause TR {contraction:.2f}x, retention {worst:.0%}; "
                  f"{lean}: trend/failure distances {trend_distance:.2f}/{failure_distance:.2f} ATR, "
                  f"last signed change {signed_change:+.2f} ATR")
        return dict(zip(SCREEN_COLUMNS, [ticker, asof.date().isoformat(), event_date.date().isoformat(),
            direction, lean, is_base, delta/start, displacement/atr0, efficiency, atr0, atr,
            volume_ratio, active, v0, float(e['pre_impulse_dollar_volume']),
            float(latest['median_dollar_volume_20']), float(e['close']), close, days,
            contraction, width_atr, max_tr_atr, worst, furthest, sign*(close-start)/displacement,
            low, high, trend_distance, failure_distance, signed_change,
            float(latest['recent_volume_ratio']), float(pause['volume'].mean()/move['volume'].mean()),
            continuation_level, failure_level, reason]))
    return None


def screen_asof(features, asof, rules=None, require_base=True):
    asof = pd.Timestamp(asof)
    calendar = pd.DatetimeIndex(sorted({d for f in features.values() for d in f.index if d <= asof}))
    rows = [_candidate_for_date(t, f, asof, rules, require_base, calendar) for t, f in features.items()]
    result = pd.DataFrame([r for r in rows if r is not None], columns=SCREEN_COLUMNS)
    return result.sort_values(['lean', 'trend_distance_atr', 'ticker']).reset_index(drop=True)


def friday_outcome(frame, setup, rules=None):
    """Resolution of Thursday-known boundaries and a separate Friday-session diagnostic."""
    r = RULES if rules is None else rules
    date = pd.Timestamp(setup['asof'])
    friday = date + pd.Timedelta(days=1)
    if date.dayofweek != 3 or date not in frame.index or friday not in frame.index:
        return None
    bar = frame.loc[friday]
    sign = 1 if setup['direction'] == 'UP' else -1
    close = float(bar['close'])
    thursday_close = float(frame.loc[date, 'close'])
    trend_level, failure_level = setup['continuation_level'], setup['failure_level']
    continues = sign * (close - trend_level) > 0
    fails = sign * (close - failure_level) < 0
    outcome = 'GOES_AGAIN' if continues else 'FAILS' if fails else 'STALLS'
    trend_touch = bool(bar['high'] > trend_level if sign == 1 else bar['low'] < trend_level)
    failure_touch = bool(bar['low'] < failure_level if sign == 1 else bar['high'] > failure_level)
    overnight = float(bar['open'] / thursday_close - 1)
    intraday = float(close / bar['open'] - 1)
    close_return = close / thursday_close - 1
    intraday_atr = sign * (close - float(bar['open'])) / setup['asof_atr']
    threshold = r['intraday_material_move_atr']
    session_label = ('INTRADAY_WITH_TREND' if intraday_atr >= threshold else
                     'INTRADAY_AGAINST_TREND' if intraday_atr <= -threshold else 'SMALL_MOVE')
    return dict(zip(OUTCOME_COLUMNS, [str(friday.date()), close_return, sign*close_return, outcome,
        overnight, sign*overnight, intraday, sign*intraday, intraday_atr, session_label, bool(continues),
        trend_touch, failure_touch, trend_touch and failure_touch]))
