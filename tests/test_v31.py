"""Legal weekly routes and public, reproducible choice policies."""
import copy
import unittest
import re
from pathlib import Path
from unittest.mock import patch
import wave

from engine import Game, BUILDINGS, UPGRADE_COSTS, EVENT_DAYS
from events import EVENTS, offer_options, describe_option
from persistence import to_data, from_data, load_game, SaveError
from i18n import translate, weekly_chinese
from tests.test_i18n import untranslated_words


class Game(Game):
    def __init__(self, seed=None, ruleset="v31"):
        super().__init__(seed, ruleset=ruleset)

def choose_carefully(game):
    """Use visible reserves and the real next forecast, not the future deck."""
    if game.day < 9:
        return 0 if game.option_error(0) is None else 1
    scores = []
    for index in (0, 1):
        if game.option_error(index):
            scores.append(float('-inf'))
            continue
        candidate = from_data(copy.deepcopy(to_data(game)))
        candidate.choose_event(index)
        forecast = candidate.forecast()
        score = (1000 * candidate.population - 800 * forecast['deaths'] - 80 * forecast['offline']
                 + candidate.happiness * 2 + min(candidate.food, 2 * candidate.population) * 2
                 + min(candidate.energy, 30) * 2 + min(candidate.materials, 60) * 4
                 + forecast['food'] * 6 + forecast['energy'] * 5 + forecast['materials'] * 10)
        scores.append(score)
    return max(range(2), key=lambda index: scores[index])


def play_route(seed=7, opening='farm', policy='careful', objective=True, rescue=False, snapshots=None, ruleset='v31'):
    game = Game(seed, ruleset=ruleset)
    sites = {'farm': (0, 0), 'mine': (0, 3), 'solar': (4, 4), 'home': (1, 0),
             'farm2': (2, 0), 'solar2': (4, 3), 'home2': (2, 1)}
    plan = [(0,'build','farm'),(1,'build','mine'),(2,'build','solar'),(3,'upgrade','solar'),
            (4,'build','home'),(6,'upgrade','farm'),(8,'upgrade','mine'),(10,'build','solar2'),
            (11,'build','farm2'),(12,'upgrade','home'),(15,'build','home2'),
            (18,'upgrade','farm2'),(20,'upgrade','solar2')]
    if opening == 'solar':
        plan[:3] = [(0,'build','solar'),(1,'build','farm'),(2,'build','mine')]
    if rescue:
        plan[:3] = [(0,'build','mine'),(4,'build','farm'),(6,'build','solar')]
    trace = []
    while game.status == 'active':
        action = 'wait'
        if rescue and game.day in (4, 5):
            game.emergency_rations()
            action = 'rations'
        if objective and game.beacon_error() is None:
            game.repair_beacon()
            action = 'HQ'
        elif plan and game.day >= plan[0][0]:
            _, method, site = plan[0]
            kind = site.rstrip('2')
            cost = BUILDINGS[kind]['cost'] if method == 'build' else UPGRADE_COSTS[kind]
            if game.materials >= cost:
                getattr(game, method)(*sites[site], *([kind] if method == 'build' else []))
                plan.pop(0)
                action = method + ' ' + site
        before = {key: getattr(game,key) for key in ('food','energy','materials','population','happiness')}
        forecast = game.forecast()
        game.next_day()
        for key, old in before.items():
            assert getattr(game,key) - old == forecast[key], (seed,game.day,key)
        if snapshots is not None:
            snapshots[(game.day,'before_choice')] = copy.deepcopy(to_data(game))
        from_data(to_data(game))
        event, choice = game.pending_event, None
        if event:
            choice = choose_carefully(game) if policy == 'careful' else 0 if policy == 'first' and not game.option_error(0) else 1
            game.choose_event(choice)
        from_data(to_data(game))
        if snapshots is not None:
            snapshots[(game.day,'after_choice')] = copy.deepcopy(to_data(game))
        trace.append((game.day, game.food, game.energy, game.materials, game.population,
                      game.happiness, game.beacon_stage, action, event, choice))
    return game, trace


class WeeklyRulesTests(unittest.TestCase):
    def test_first_eight_weeks_match_one_hundred_original_openings(self):
        for seed in range(100):
            _, old = play_route(seed, ruleset='v30')
            _, new = play_route(seed)
            self.assertEqual([row[:7] for row in old[:8]], [row[:7] for row in new[:8]], seed)

    def test_twelve_unique_events_and_recovery_slots(self):
        for seed in range(100):
            game = Game(seed)
            self.assertEqual(set(game.event_order), set(EVENTS))
            self.assertEqual(len(game.event_order), 12)
            self.assertEqual(set(game.event_order[i] for i in (2,5,8)), {'cold','dust','filters'})
            self.assertEqual(game.event_order[-1], 'community')
            if 'storm' not in game.event_order[:2]:
                self.assertEqual(game.event_order[3], 'storm')
            from_data(to_data(game))

    def test_both_normal_openings_and_recovery_can_win(self):
        for opening, rescue in (('farm',False),('solar',False),('farm',True)):
            game, trace = play_route(7,opening=opening,rescue=rescue)
            self.assertEqual(game.status,'won',(opening,rescue,trace[-1]))
        self.assertEqual(len([row for row in play_route()[1] if row[-2]]),12)

    def test_costs_scale_by_population_and_phase_not_inventory(self):
        self.assertEqual(offer_options('cold',9,6)[0]['cost'],{'energy':20})
        self.assertEqual(offer_options('cold',22,6)[0]['cost'],{'energy':23})
        self.assertEqual(offer_options('festival',5,5)[0]['cost'],{'food':10,'energy':4})
        snapshots={};play_route(snapshots=snapshots)
        data=snapshots[(22,'before_choice')]
        game=from_data(data)
        expected=game.event_options()
        game.food=game.energy=game.materials=999
        self.assertEqual(game.event_options(),expected)

    def test_offer_round_trip_and_tampered_cost_rejection(self):
        snapshots={};play_route(snapshots=snapshots)
        for day in EVENT_DAYS:
            data=snapshots[(day,'before_choice')]
            self.assertEqual(to_data(from_data(data)),data)
        bad=copy.deepcopy(snapshots[(9,'before_choice')])
        first=bad['event_snapshot']['options'][0]
        first['cost'][next(iter(first['cost']))]=0
        with self.assertRaises(SaveError):from_data(bad)

    def test_event_snapshot_is_detached_from_ui_return_value(self):
        snapshots={};play_route(snapshots=snapshots)
        game=from_data(snapshots[(9,'before_choice')])
        before=copy.deepcopy(to_data(game))
        game.event_view()['options'][0]['cost'].clear()
        self.assertEqual(to_data(game),before)

    def test_locked_quote_rejects_float_or_boolean_number_substitution(self):
        snapshots={};play_route(snapshots=snapshots)
        for value in (4.0,True):
            bad=copy.deepcopy(snapshots[(2,'before_choice')])
            bad['event_snapshot']['population']=value
            with self.assertRaises(SaveError):from_data(bad)

    def test_cold_reduces_total_linked_farm_output_and_expires(self):
        game=Game(7);game.build(0,0,'farm')
        game.grid[1][0]='home';game.levels[1][0]=1
        game.effects={'cold_snap':2};game.energy=30
        self.assertEqual((game.forecast()['farm_loss'],game.forecast()['food']),(2,2))
        game.next_day();self.assertEqual(game.effects,{'cold_snap':1})
        game.next_day();self.assertEqual(game.effects,{})

    def test_dust_and_storm_do_not_multiply(self):
        game=Game(7);game.build(0,0,'solar')
        game.effects={'solar_storm':2,'dust_cloud':3}
        self.assertEqual(game.forecast()['solar'],3)

    def test_filter_power_is_paid_only_for_powered_facilities(self):
        game=Game(7);game.build(0,0,'farm')
        game.effects={'filter_load':3};game.energy=3
        self.assertEqual((game.forecast()['farms'],game.forecast()['filter_power']),(0,0))
        game.energy=4
        self.assertEqual((game.forecast()['farms'],game.forecast()['filter_power']),(1,1))

    def test_growth_and_rations_still_use_same_settlement(self):
        game=Game(7);game.day=3;game.food=40
        self.assertTrue(game.forecast()['growth'])
        game.emergency_rations()
        self.assertFalse(game.forecast()['growth'])
        game.next_day();self.assertEqual((game.population,game.food),(4,38))

    def test_late_ore_has_visible_improved_income(self):
        option=offer_options('deposit',14,7)[0]
        self.assertEqual(option['ore_bonus'],8)
        self.assertIn('+8 Materials',describe_option(option))
        self.assertNotIn('ore_bonus',offer_options('deposit',2,4)[0])

    def test_invalid_ruleset_snapshot_and_spacing_rejected(self):
        for field,value in (('ruleset','future'),('ruleset',[]),('event_snapshot',{})):
            data=to_data(Game(7));data[field]=value
            with self.assertRaises(SaveError):from_data(data)
        data=to_data(Game(7));data['event_order'][2],data['event_order'][4]=data['event_order'][4],data['event_order'][2]
        with self.assertRaises(SaveError):from_data(data)

    def test_legacy_thirty_day_saves_keep_old_rules_and_eight_events(self):
        folder=Path(__file__).resolve().parents[1]/'examples/legacy/V3.0'
        game=load_game(folder/'day29_before_arrival.json')
        self.assertEqual((game.ruleset,len(game.event_order)),('v30',8))
        game.next_day();self.assertEqual(game.result(),('New Eden',441))
        data=to_data(game)
        self.assertEqual(to_data(from_data(data)),data)

    def test_weekly_text_does_not_change_sky_or_external_paths(self):
        self.assertEqual(weekly_chinese('第3天，天空明亮。每天1食物。'),'第3周，天空明亮。每周1食物。')
        self.assertEqual(translate('Saved to Week.json','zh_CN'),'已保存至 Week.json')

    def test_complete_routes_translate_reports_logs_and_scaled_choices(self):
        snapshots={};play_route(snapshots=snapshots)
        for data in snapshots.values():
            game=from_data(data)
            for text in (*game.log,game.last_report,game.planning_report()):
                self.assertFalse(untranslated_words(translate(text,'zh_CN')),text)
            if game.pending_event:
                for option in game.event_options():
                    self.assertFalse(untranslated_words(translate(describe_option(option),'zh_CN')),describe_option(option))


class SoundTests(unittest.TestCase):
    def test_assets_are_nine_short_original_wavs(self):
        folder=Path(__file__).resolve().parents[1]/'assets'
        self.assertEqual({p.stem for p in folder.glob('*.wav')},{'build','event','warning','beacon','settle','choice','ration','victory','failure'})
        for path in folder.glob('*.wav'):
            with wave.open(str(path)) as stream:
                self.assertEqual((stream.getnchannels(),stream.getsampwidth()),(1,2))
                self.assertLess(stream.getnframes()/stream.getframerate(),1)

    def test_default_silent_and_failure_disables_audio(self):
        from soundfx import SoundPlayer
        player=SoundPlayer();self.assertFalse(player.enabled)
        self.assertFalse(player.play('build'))
        with patch('soundfx.winsound') as backend:
            backend.PlaySound.side_effect=RuntimeError('no device')
            player.available=player.enabled=True
            self.assertFalse(player.play('event'))
            self.assertFalse(player.available)
            self.assertFalse(player.enabled)

    def test_muted_and_unsupported_platform_are_safe(self):
        from soundfx import SoundPlayer
        with patch('soundfx.winsound',None):
            player=SoundPlayer();self.assertFalse(player.available)
            self.assertFalse(player.play('beacon'));player.stop()
