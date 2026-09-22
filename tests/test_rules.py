import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from src.screen import RULES, build_features, screen_asof, friday_outcome, lean_from_conditions
from src.data import validate_bars
from src.backtest import thursday_dates, summarize
from pathlib import Path


class RuleTests(unittest.TestCase):
    def test_expanded_universe_is_unique_and_has_demo_fixture(self):
        universe = pd.read_csv('config/universe.csv')
        fixture = pd.read_csv('config/universe_56.csv')
        self.assertGreaterEqual(len(universe), 300)
        self.assertEqual(len(universe), universe.ticker.nunique())
        self.assertEqual(len(fixture), 56)
        self.assertTrue(set(fixture.ticker).issubset(set(universe.ticker)))

    def frame(self):
        dates = pd.bdate_range('2025-01-01', periods=100)
        close = np.full(100, 100.0)
        close[76:81] = [101.6, 103.2, 104.8, 106.4, 108]
        close[81:] = 108
        close[81:84] = [108, 107.9, 108.1]
        volume = np.full(100, 2_000_000.0)
        volume[76:81] = 4_000_000
        high, low = close+1, close-1
        high[76:81], low[76:81] = close[76:81]+.5, close[76:81]-.5
        high[81:], low[81:] = 108.3, 107.7
        return pd.DataFrame(dict(open=close, high=high, low=low, close=close, volume=volume), index=dates)

    def screen(self, f, rules=None, require_base=True):
        return screen_asof(build_features({'AAA': f}, rules), f.index[83], rules, require_base)

    def test_nonempty_screen_and_temporal_isolation(self):
        f = self.frame()
        asof = f.index[83]
        full = self.screen(f)
        self.assertEqual(len(full), 1)
        self.assertEqual(full.iloc[0]['consolidation_days'], 3)
        self.assertEqual(full.iloc[0]['lean'], 'CONTINUATION_WATCH')
        truncated = screen_asof(build_features({'AAA': f.loc[:asof]}), asof)
        f.loc[f.index > asof, ['open','high','low','close','volume']] *= 100
        assert_frame_equal(full, truncated)
        assert_frame_equal(full, self.screen(f))

    def test_baselines_precede_entire_impulse(self):
        f = self.frame()
        out = build_features({'AAA': f})['AAA']
        self.assertEqual(out.iloc[80]['pre_impulse_atr'], 2)
        self.assertEqual(out.iloc[80]['pre_impulse_volume_median'], 2_000_000)
        f.loc[f.index[76:81], 'volume'] *= 100
        self.assertEqual(build_features({'AAA': f})['AAA'].iloc[80]['pre_impulse_volume_median'], 2_000_000)

    def test_single_volume_spike_does_not_establish_participation(self):
        f = self.frame()
        f.loc[f.index[76:81], 'volume'] = [1_000_000]*4+[14_000_000]
        self.assertTrue(self.screen(f, require_base=False).empty)

    def test_liquidity_is_independent_of_relative_volume(self):
        f = self.frame()
        f['volume'] /= 1000
        self.assertTrue(self.screen(f).empty)

    def test_high_absolute_move_can_fail_relative_hurdle(self):
        f = self.frame()
        f.loc[f.index[:76], 'high'] = 105
        f.loc[f.index[:76], 'low'] = 95
        self.assertTrue(self.screen(f, require_base=False).empty)

    def test_churn_fails_directional_efficiency(self):
        f = self.frame()
        f.loc[f.index[76:81], 'close'] = [108, 100, 110, 101, 108]
        f.loc[f.index[76:81], 'open'] = f.loc[f.index[76:81], 'close']
        f.loc[f.index[76:81], 'high'] = f.loc[f.index[76:81], 'close']+.5
        f.loc[f.index[76:81], 'low'] = f.loc[f.index[76:81], 'close']-.5
        self.assertTrue(self.screen(f, require_base=False).empty)

    def test_uncontracted_pause_fails_while_impulse_reference_survives(self):
        f = self.frame()
        f.loc[f.index[81:84], 'high'] = 110
        f.loc[f.index[81:84], 'low'] = 106
        self.assertTrue(self.screen(f).empty)
        self.assertEqual(len(self.screen(f, require_base=False)), 1)

    def test_deep_retracement_fails_retention(self):
        f = self.frame()
        f.loc[f.index[81:84], ['open','close']] = [[104,104],[103.9,103.9],[103.8,103.8]]
        f.loc[f.index[81:84], 'high'] = 104.2
        f.loc[f.index[81:84], 'low'] = 103.6
        r = {**RULES, 'max_tr_contraction': 10, 'max_pause_daily_tr_atr': 10, 'max_pause_width_atr': 10,
             'min_pause_sessions': 3, 'max_pause_sessions': 3}
        self.assertTrue(self.screen(f, r).empty)
        reference = self.screen(f, r, require_base=False)
        self.assertEqual(len(reference), 1)
        self.assertLess(reference.iloc[0]['worst_retention'], .5)

    def test_same_shape_is_price_scale_invariant(self):
        f = self.frame()
        original = self.screen(f).iloc[0]
        f[['open','high','low','close']] *= 10
        scaled = self.screen(f).iloc[0]
        for key in ['impulse_atr','path_efficiency','tr_contraction_ratio','worst_retention','trend_distance_atr']:
            self.assertAlmostEqual(original[key], scaled[key])
        self.assertEqual(original['lean'], scaled['lean'])

    def test_further_trending_is_not_a_pause(self):
        f = self.frame()
        f.loc[f.index[81:84], ['open','close']] = [[109,109],[110,110],[111,111]]
        f.loc[f.index[81:84], 'high'] = [109.2,110.2,111.2]
        f.loc[f.index[81:84], 'low'] = [108.8,109.8,110.8]
        r = {**RULES, 'min_pause_sessions': 3, 'max_pause_sessions': 3}
        self.assertEqual(len(self.screen(f,r,require_base=False)),1)
        self.assertTrue(self.screen(f,r).empty)

    def test_unrelated_peers_do_not_change_a_qualified_name(self):
        f = self.frame()
        alone = self.screen(f)
        peer = f.copy()
        peer['volume'] /= 1000
        together = screen_asof(build_features({'AAA': f, 'BBB': peer}), f.index[83])
        assert_frame_equal(alone, together)

    def test_downward_geometry_is_symmetric(self):
        f = self.frame()
        f[['open','high','low','close']] = 200-f[['open','high','low','close']]
        f[['high','low']] = f[['low','high']].to_numpy()
        row = self.screen(f).iloc[0]
        self.assertEqual(row['direction'], 'DOWN')
        self.assertEqual(row['lean'], 'CONTINUATION_WATCH')
        self.assertLess(row['continuation_level'], row['failure_level'])

    def test_lean_needs_movement_toward_boundary(self):
        self.assertEqual(lean_from_conditions(.1,.8,-.1), 'UNRESOLVED')
        self.assertEqual(lean_from_conditions(.1,.8,.1), 'CONTINUATION_WATCH')
        self.assertEqual(lean_from_conditions(.8,.1,-.1), 'FAILURE_RISK')
        self.assertEqual(lean_from_conditions(.1,.1,0), 'UNRESOLVED')

    def test_missing_ticker_session_is_not_counted_as_pause(self):
        f = self.frame()
        other = f.copy()
        f = f.drop(f.index[82])
        result = screen_asof(build_features({'AAA': f, 'BBB': other}), other.index[83])
        self.assertNotIn('AAA', result['ticker'].tolist())

    def outcome_fixture(self):
        dates = pd.to_datetime(['2025-01-02','2025-01-03'])
        f = pd.DataFrame(dict(open=[101,104],high=[102,105],low=[100,102.5],close=[101,103],volume=[1e6,1e6]),index=dates,dtype=float)
        row = dict(asof='2025-01-02',direction='UP',asof_atr=2,continuation_level=102.2,failure_level=99.8)
        return f,row

    def test_gap_resolution_is_not_intraday_continuation(self):
        f,row = self.outcome_fixture()
        out = friday_outcome(f,row)
        self.assertEqual(out['outcome'], 'GOES_AGAIN')
        self.assertEqual(out['intraday_outcome'], 'INTRADAY_AGAINST_TREND')
        self.assertAlmostEqual((1+out['overnight_return'])*(1+out['intraday_return'])-1,out['friday_return'])

    def test_buffer_equality_and_both_touches(self):
        f,row = self.outcome_fixture()
        f.iloc[1,f.columns.get_loc('close')] = 102.2
        f.iloc[1,f.columns.get_loc('low')] = 99
        out = friday_outcome(f,row)
        self.assertEqual(out['outcome'], 'STALLS')
        self.assertTrue(out['both_sides_touched'])
        f.iloc[1,f.columns.get_loc('close')] = 99.7
        self.assertEqual(friday_outcome(f,row)['outcome'], 'FAILS')

    def test_down_outcome_and_missing_friday(self):
        f,row = self.outcome_fixture()
        row.update(direction='DOWN',continuation_level=99.8,failure_level=102.2)
        self.assertEqual(friday_outcome(f,row)['outcome'], 'FAILS')
        f.index = pd.to_datetime(['2025-01-02','2025-01-10'])
        self.assertIsNone(friday_outcome(f,row))

    def test_invalid_bar_rejected(self):
        f = self.frame()
        f.iloc[5,f.columns.get_loc('high')] = 1
        with self.assertRaises(ValueError):
            validate_bars(f)

    def test_calendar_and_empty_summary(self):
        dates = thursday_dates('2026-09-21',26)
        self.assertEqual(len(dates),26)
        self.assertTrue((dates.dayofweek == 3).all())
        self.assertEqual(str(dates[-1].date()), '2026-09-17')
        result = summarize(pd.DataFrame()).iloc[0]
        self.assertEqual(result['observations'],0)
        self.assertTrue(pd.isna(result['goes_again_rate']))


if __name__ == '__main__':
    unittest.main()
