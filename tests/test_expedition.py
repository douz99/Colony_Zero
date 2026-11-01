"""Thirty-day routes, objective deadlines, recovery and schema-4 validation."""

import copy
from collections import Counter
from pathlib import Path
import unittest

from engine import BEACON_STAGES, BUILDINGS, V30_EVENT_DAYS as EVENT_DAYS, Game, RuleError, UPGRADE_COSTS, facility_effect
from events import EVENTS as ALL_EVENTS
from engine import V30_EVENTS
EVENTS = {key: ALL_EVENTS[key] for key in V30_EVENTS}
from i18n import translate
from persistence import SaveError, from_data, load_game, to_data
from tests.test_i18n import untranslated_words


class Game(Game):
    def __init__(self, seed=None):
        super().__init__(seed, ruleset="v30")

def play_expedition(seed=7, objective=True, opening="farm", rescue=False, snapshots=None):
    """A reproducible plan with ordinary starting resources and legal actions."""
    game = Game(seed)
    sites = {"farm": (0, 0), "mine": (0, 3), "solar": (4, 4), "home": (1, 0),
             "farm2": (2, 0), "solar2": (4, 3), "home2": (2, 1)}
    plan = [(0, "build", "farm"), (1, "build", "mine"), (2, "build", "solar"),
            (3, "upgrade", "solar"), (4, "build", "home"), (6, "upgrade", "farm"),
            (8, "upgrade", "mine"), (10, "build", "solar2"), (11, "build", "farm2"),
            (12, "upgrade", "home"), (15, "build", "home2"), (18, "upgrade", "farm2"),
            (20, "upgrade", "solar2")]
    if opening == "solar":
        plan[:3] = [(0, "build", "solar"), (1, "build", "farm"), (2, "build", "mine")]
    if rescue:
        plan[:3] = [(0, "build", "mine"), (4, "build", "farm"), (6, "build", "solar")]
    trace = []
    while game.status == "active":
        action = "wait"
        if rescue and game.day in (4, 5):
            game.emergency_rations()
            action = "rations"
        if objective and game.beacon_error() is None:
            game.repair_beacon()
            action = "HQ" if action == "wait" else action + "; HQ"
        elif plan and game.day >= plan[0][0]:
            _, method, site = plan[0]
            kind = site.rstrip("2")
            cost = BUILDINGS[kind]["cost"] if method == "build" else UPGRADE_COSTS[kind]
            if game.materials >= cost:
                getattr(game, method)(*sites[site], *([kind] if method == "build" else []))
                plan.pop(0)
                action = method + " " + site if action == "wait" else action + "; " + method + " " + site
        before = {key: getattr(game, key) for key in ("food", "energy", "materials", "population", "happiness")}
        forecast = game.forecast()
        game.next_day()
        for key, old in before.items():
            if getattr(game, key) - old != forecast[key]:
                raise AssertionError((game.day, key, "forecast disagrees with settlement"))
        if snapshots is not None:
            snapshots[(game.day, "before_choice")] = copy.deepcopy(to_data(game))
        from_data(to_data(game))
        event = game.pending_event
        if event:
            game.choose_event(0 if game.option_error(0) is None else 1)
        from_data(to_data(game))
        if snapshots is not None:
            snapshots[(game.day, "after_choice")] = copy.deepcopy(to_data(game))
        trace.append((game.day, game.food, game.energy, game.materials, game.population,
                      game.happiness, game.beacon_stage, action, event))
    return game, trace


class ExpeditionTests(unittest.TestCase):
    def test_default_campaign_and_eight_unique_events(self):
        game, trace = play_expedition()
        self.assertEqual((game.day, game.campaign_days, game.status), (30, 30, "won"))
        self.assertEqual(Counter(row[-1] for row in trace if row[-1]), Counter(list(EVENTS)))
        self.assertEqual([row[0] for row in trace if row[-1]], list(EVENT_DAYS))
        self.assertEqual(game.result(), ("New Eden", 441))
        self.assertEqual((game.food, game.energy, game.materials, game.population, game.happiness), (206, 126, 51, 13, 91))

    def test_two_openings_and_delayed_food_recovery(self):
        for opening, rescue in (("farm", False), ("solar", False), ("farm", True)):
            game, _ = play_expedition(opening=opening, rescue=rescue)
            self.assertEqual(game.status, "won")
            self.assertEqual(game.beacon_stage, 3)
            self.assertEqual(game.ration_uses, 2 if rescue else 0)

    def test_one_hundred_shuffles_survive_with_main_plan(self):
        for seed in range(100):
            game, _ = play_expedition(seed)
            self.assertEqual(game.status, "won", seed)

    def test_survival_without_beacon_is_not_victory(self):
        game, _ = play_expedition(objective=False)
        self.assertGreater(game.population, 0)
        self.assertEqual((game.day, game.status, game.result()[0]), (30, "lost", "Stranded Colony"))
        self.assertEqual(to_data(from_data(to_data(game))), to_data(game))
        with self.assertRaises(RuleError):
            game.next_day()

    def test_neglect_has_a_real_failure_path(self):
        game = Game(7)
        while game.status == "active":
            game.next_day()
            if game.pending_event:
                game.choose_event(1)
        self.assertEqual((game.status, game.population, game.result()[0]), ("lost", 0, "Silent Beacon"))
        self.assertLess(game.day, 30)

    def test_beacon_unlock_costs_and_atomic_rejection(self):
        game = Game(7)
        before = copy.deepcopy(to_data(game))
        with self.assertRaises(RuleError):
            game.repair_beacon()
        self.assertEqual(to_data(game), before)
        # Isolated rule fixture: full routes above pay for every real action.
        game.day = 6
        game.energy = 8
        game.repair_beacon()
        self.assertEqual((game.beacon_stage, game.materials, game.energy, game.built_today), (1, 24, 0, True))
        with self.assertRaises(RuleError):
            game.build(0, 0, "farm")
        game.day = 14
        game.built_today = False
        before = copy.deepcopy(to_data(game))
        with self.assertRaises(RuleError):
            game.repair_beacon()
        self.assertEqual(to_data(game), before)
        self.assertEqual(sum(s[1] for s in BEACON_STAGES), 82)
        self.assertEqual(sum(s[2] for s in BEACON_STAGES), 58)

    def test_beacon_and_construction_share_the_crew(self):
        game = Game(7)
        game.day = 6
        game.build(0, 0, "solar")
        self.assertIn("busy", game.beacon_error())
        before = to_data(game)
        with self.assertRaises(RuleError):
            game.repair_beacon()
        self.assertEqual(to_data(game), before)

    def test_rations_halve_odd_meals_pause_growth_and_expire(self):
        game = Game(7)
        game.day = 3
        game.population = 5
        game.food = 40
        game.emergency_rations()
        self.assertEqual((game.food_demand, game.happiness), (3, 62))
        self.assertFalse(game.built_today)
        self.assertFalse(game.forecast()["growth"])
        self.assertIn("emergency rations", game.forecast()["growth_reason"])
        game.next_day()
        self.assertEqual((game.population, game.food, game.ration_days, game.food_demand), (5, 37, 0, 5))

    def test_rations_prevent_an_actual_forecast_death(self):
        game = Game(7)
        game.food = 2
        self.assertEqual(game.forecast()["deaths"], 1)
        game.emergency_rations()
        self.assertEqual(game.forecast()["deaths"], 0)
        game.next_day()
        self.assertEqual(game.population, 4)

    def test_only_two_orders_and_no_double_activation(self):
        game = Game(7)
        game.emergency_rations()
        for _ in range(2):
            before = to_data(game)
            with self.assertRaises(RuleError):
                game.emergency_rations()
            self.assertEqual(to_data(game), before)
        game.next_day()
        game.emergency_rations()
        game.next_day()
        game.choose_event(1)
        with self.assertRaises(RuleError):
            game.emergency_rations()

    def test_council_blocks_both_new_actions(self):
        game = Game(7)
        game.next_day()
        game.next_day()
        for action in (game.repair_beacon, game.emergency_rations):
            before = to_data(game)
            with self.assertRaises(RuleError):
                action()
            self.assertEqual(to_data(game), before)

    def test_morale_settles_toward_78_without_free_100(self):
        for current, expected in ((70, 71), (78, 78), (90, 89)):
            game = Game()
            game.happiness = current
            self.assertEqual(game.forecast()["new_happiness"], expected)

    def test_new_food_outputs_and_fourth_day_growth(self):
        self.assertEqual(facility_effect("farm", 1), "3 Energy -> 6 Food/day")
        self.assertEqual(facility_effect("farm", 2), "4 Energy -> 9 Food/day")
        game = Game()
        game.build(0, 0, "farm")
        self.assertEqual(game.forecast()["food"], 2)
        game.day = 2
        self.assertFalse(game.forecast()["growth"])
        game.day = 3
        self.assertTrue(game.forecast()["growth"])

    def test_save_resume_every_turn_and_pending_rations(self):
        snapshots = {}
        expected, _ = play_expedition(snapshots=snapshots)
        resumed = from_data(snapshots[(29, "after_choice")])
        resumed.next_day()
        self.assertEqual(to_data(resumed), to_data(expected))
        game = Game()
        game.emergency_rations()
        restored = from_data(copy.deepcopy(to_data(game)))
        game.next_day()
        restored.next_day()
        self.assertEqual(to_data(restored), to_data(game))

    def test_invalid_new_save_fields_are_rejected(self):
        cases = (("campaign_days", 20), ("campaign_days", True), ("beacon_stage", 4),
                 ("beacon_stage", 1), ("ration_uses", 3), ("ration_uses", True),
                 ("ration_days", 2), ("ration_days", 1), ("event_order", ["storm"] * 8),
                 ("day", 31))
        for key, value in cases:
            data = to_data(Game())
            data[key] = value
            with self.subTest(field=key, value=value), self.assertRaises(SaveError):
                from_data(data)

    def test_old_examples_keep_dates_timers_and_original_endings(self):
        folder = Path(__file__).resolve().parents[1] / "examples" / "legacy"
        groups = {"V2.x": (8, "v20", 15, 6), "V3.0": (10, "v30", 30, 8),
                  "V3.1": (12, "v31", 30, 12)}
        self.assertEqual({p.name for p in folder.iterdir() if p.is_dir()}, set(groups))
        self.assertEqual(len(list(folder.rglob("*.json"))), 30)
        for version, (count, ruleset, days, events) in groups.items():
            paths = list((folder / version).glob("*.json"))
            self.assertEqual(len(paths), count)
            for path in paths:
                with self.subTest(version=version, save=path.name):
                    game = load_game(path)
                    self.assertEqual((game.ruleset, game.campaign_days, len(game.event_order)),
                                     (ruleset, days, events))
                    if days == 15:
                        self.assertEqual(game.beacon_stage, 0)
        ended = load_game(folder / "V2.x" / "day15_noisy_comparison.json")
        self.assertEqual((ended.status, ended.day), ("won", 15))
        storm = load_game(folder / "V2.x" / "day04_storm_active.json")
        self.assertEqual(storm.effects, {"solar_storm": 2})

    def test_chinese_new_route_reports_mission_and_crew_feedback(self):
        snapshots = {}
        play_expedition(snapshots=snapshots, rescue=True)
        for data in snapshots.values():
            game = from_data(data)
            for text in (*game.log, game.last_report, game.planning_report(), game.mission_summary(), game.crew_message(), game.summary()):
                self.assertFalse(untranslated_words(translate(text, "zh_CN")), text)


if __name__ == "__main__":
    unittest.main()
