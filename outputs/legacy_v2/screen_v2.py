"""Explicit daily-price proxy rules; no fitted probabilities."""
from __future__ import annotations
import numpy as np
import pandas as pd

MIN_IMPULSE_RETURN = 0.06
MIN_VOLUME_RATIO = 1.30
MIN_CONSOLIDATION_DAYS = 2
MAX_CONSOLIDATION_DAYS = 5
MAX_DAILY_CONSOLIDATION_RETURN = 0.02
MAX_CONSOLIDATION_RANGE = 0.07
MAX_EVENT_CLOSE_DRIFT = 0.04
MIN_CROWD_PERCENTILE = 0.75
FRIDAY_MOVE = 0.02
POSITION_EDGE = 0.75
SCREEN_COLUMNS = ['ticker', 'asof', 'event_date', 'impulse_return_5d', 'impulse_volume_ratio',
    'crowd_rank_abs_return', 'rank_universe_size', 'consolidation_days', 'consolidation_range',
    'max_abs_daily_return', 'event_close_drift', 'consolidation_low', 'consolidation_high',
    'asof_close', 'signed_position', 'recent_volume_ratio', 'median_dollar_volume_20',
    'impulse_range', 'range_contraction_ratio', 'impulse_retention', 'direction', 'lean', 'reason']


def _feature_frame(frame):
    out = frame.copy().sort_index()
    out['ret_1d'] = out['close'].pct_change(fill_method=None)
    out['ret_5d'] = out['close'].pct_change(5, fill_method=None)
    for days in (20, 60):
        out[f'volume_median_{days}'] = out['volume'].shift(1).rolling(days).median()
    out['volume_ratio'] = out['volume'] / out['volume_median_60'].replace(0, np.nan)
    out['recent_volume_ratio'] = out['volume'] / out['volume_median_20'].replace(0, np.nan)
    out['median_dollar_volume_20'] = (out['close'] * out['volume']).shift(1).rolling(20).median()
    return out


def build_features(data):
    return {ticker: _feature_frame(frame) for ticker, frame in data.items()}


def _cross_sectional_rank(features, date):
    values = {t: abs(f.loc[date, 'ret_5d']) for t, f in features.items()
              if date in f.index and pd.notna(f.loc[date, 'ret_5d'])}
    return pd.Series(values, dtype=float).rank(pct=True)


def lean_from_position(position):
    if position >= POSITION_EDGE:
        return 'TREND_SIDE'
    if position <= 1 - POSITION_EDGE:
        return 'OPPOSITE_SIDE'
    return 'MID_RANGE'


def _candidate_for_date(ticker, frame, features, asof, rank_cache=None):
    if asof not in frame.index:
        return None
    pos = frame.index.get_loc(asof)
    if not isinstance(pos, (int, np.integer)) or pos < 62:
        return None
    rank_cache = {} if rank_cache is None else rank_cache
    # Longest qualifying pause wins; this preserves the original tie policy explicitly.
    for days in range(MAX_CONSOLIDATION_DAYS, MIN_CONSOLIDATION_DAYS - 1, -1):
        event_pos = pos - days
        if event_pos < 60:
            continue
        event_date = frame.index[event_pos]
        event = frame.iloc[event_pos]
        if not np.isfinite(event['volume_ratio']) or abs(event['ret_5d']) < MIN_IMPULSE_RETURN:
            continue
        if event['volume_ratio'] < MIN_VOLUME_RATIO:
            continue
        if event_date not in rank_cache:
            rank_cache[event_date] = _cross_sectional_rank(features, event_date)
        ranks = rank_cache[event_date]
        rank = ranks.get(ticker, np.nan)
        if pd.isna(rank) or rank < MIN_CROWD_PERCENTILE:
            continue
        cons = frame.iloc[event_pos + 1:pos + 1]
        daily_max = cons['ret_1d'].abs().max()
        low, high = float(cons['low'].min()), float(cons['high'].max())
        span = high / low - 1
        close = float(frame.iloc[pos]['close'])
        drift = close / event['close'] - 1
        if daily_max > MAX_DAILY_CONSOLIDATION_RETURN or span > MAX_CONSOLIDATION_RANGE:
            continue
        if abs(drift) > MAX_EVENT_CLOSE_DRIFT:
            continue
        sign = 1 if event['ret_5d'] > 0 else -1
        location = (close - low) / (high - low) if high > low else 0.5
        signed_position = float(np.clip(location if sign == 1 else 1 - location, 0, 1))
        lean = lean_from_position(signed_position)
        impulse = frame.iloc[event_pos - 4:event_pos + 1]
        impulse_range = float(impulse['high'].max() / impulse['low'].min() - 1)
        start_close = float(frame.iloc[event_pos - 5]['close'])
        retention = (close - start_close) / (event['close'] - start_close)
        volume = float(frame.iloc[pos]['recent_volume_ratio'])
        direction = 'UP' if sign == 1 else 'DOWN'
        reason = (f"{event['ret_5d']:+.1%} / 5d; endpoint volume {event['volume_ratio']:.2f}x; "
                  f"{days}d pause, range {span:.1%}; trend-side position {signed_position:.0%} "
                  f"({direction}); latest volume {volume:.2f}x, descriptive only")
        return dict(zip(SCREEN_COLUMNS, [ticker, asof.date().isoformat(), event_date.date().isoformat(),
            float(event['ret_5d']), float(event['volume_ratio']), float(rank), len(ranks), days,
            float(span), float(daily_max), float(drift), low, high, close, signed_position, volume,
            float(frame.iloc[pos]['median_dollar_volume_20']), impulse_range,
            span / impulse_range if impulse_range > 0 else np.nan, float(retention), direction, lean, reason]))
    return None


def screen_asof(features, asof):
    ranks = {}
    rows = [_candidate_for_date(t, f, features, pd.Timestamp(asof), ranks) for t, f in features.items()]
    result = pd.DataFrame([r for r in rows if r is not None], columns=SCREEN_COLUMNS)
    return result.sort_values(['lean', 'signed_position'], ascending=[True, False]).reset_index(drop=True)


def classify_return(signed_return):
    if signed_return >= FRIDAY_MOVE:
        return 'GOES_AGAIN'
    if signed_return <= -FRIDAY_MOVE:
        return 'REVERSES'
    return 'STALLS'


def friday_outcome(frame, event_date, asof, direction, consolidation_low=None, consolidation_high=None):
    """Exact next-day Friday only; do not replace missing Fridays with later sessions."""
    date = pd.Timestamp(asof)
    friday = date + pd.Timedelta(days=1)
    if date.dayofweek != 3 or date not in frame.index or friday not in frame.index:
        return None
    thursday_close = float(frame.loc[date, 'close'])
    bar = frame.loc[friday]
    sign = 1 if direction == 'UP' else -1
    close_return = float(bar['close'] / thursday_close - 1)
    overnight = float(bar['open'] / thursday_close - 1)
    intraday = float(bar['close'] / bar['open'] - 1)
    result = dict(friday=friday.date().isoformat(), friday_return=close_return,
        signed_return=sign * close_return, outcome=classify_return(sign * close_return),
        overnight_return=overnight, signed_overnight_return=sign * overnight,
        intraday_return=intraday, signed_intraday_return=sign * intraday,
        intraday_outcome=classify_return(sign * intraday))
    if consolidation_low is not None and consolidation_high is not None:
        result['closed_beyond_trend_boundary'] = bool(bar['close'] > consolidation_high if sign == 1 else bar['close'] < consolidation_low)
        result['touched_beyond_trend_boundary'] = bool(bar['high'] > consolidation_high if sign == 1 else bar['low'] < consolidation_low)
    return result
