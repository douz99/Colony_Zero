"""Upgrade costs, level-aware power allocation and version-1 migration."""

import copy
import unittest

from engine import BUILDINGS, Game, RuleError, UPGRADE_COSTS, facility_effect
from persistence import SaveError, from_data, to_data
from tests.test_engine import safe_choice


# Regression fixtures explicitly retain the original 15-day rules.
_CurrentGame = Game
class Game(_CurrentGame):
    def __init__(self, seed=None):
        super().__init__(seed=seed, campaign_days=15)

class UpgradeTests(unittest.TestCase):
    def ready_facility(self, kind):
        game = Game(7)
        game.build(0, 0, kind)
        game.next_day()
        return game

    def test_all_four_upgrades_cost_and_limit(self):
        for kind in BUILDINGS:
            with self.subTest(kind=kind):
                game = self.ready_facility(kind)
                before = game.materials
                game.upgrade(0, 0)
                self.assertEqual(game.materials, before - UPGRADE_COSTS[kind])
                self.assertEqual(game.levels[0][0], 2)
                self.assertEqual(game.upgrade_count, 1)
                self.assertIn("L2", game.log[-1])
                with self.assertRaises(RuleError):
                    game.upgrade(0, 0)

    def test_upgrade_and_build_share_daily_action(self):
        game = Game(7)
        game.build(0, 0, "solar")
        with self.assertRaises(RuleError):
            game.upgrade(0, 0)
        game.next_day()
        game.upgrade(0, 0)
        with self.assertRaises(RuleError):
            game.build(0, 1, "home")

    def test_upgrade_rejections_are_atomic(self):
        game = self.ready_facility("farm")
        for location in ((2, 2), (0, 1), (-1, 0), (True, 0), (5, 0)):
            before = copy.deepcopy(to_data(game))
            with self.assertRaises(RuleError):
                game.upgrade(*location)
            self.assertEqual(to_data(game), before)
        game.materials = 0
        with self.assertRaises(RuleError):
            game.upgrade(0, 0)

    def test_pending_event_blocks_upgrade(self):
        game = self.ready_facility("solar")
        game.next_day()
        with self.assertRaises(RuleError):
            game.upgrade(0, 0)
        safe_choice(game)
        game.upgrade(0, 0)

    def test_level_two_outputs_and_housing(self):
        for kind, expected in (("solar", (-4, 12, 0)), ("farm", (8, -4, 0)), ("mine", (-4, -4, 9))):
            game = self.ready_facility(kind)
            game.upgrade(0, 0)
            game.energy = 30
            forecast = game.forecast()
            self.assertEqual(tuple(forecast[key] for key in ("food", "energy", "materials")),
                             expected)
        game = self.ready_facility("home")
        self.assertEqual(game.housing, 10)
        game.upgrade(0, 0)
        self.assertEqual(game.housing, 12)
        self.assertEqual(facility_effect("farm", 2, campaign_days=15), "4 Energy -> 12 Food/day")

    def test_expensive_farm_can_be_skipped_for_affordable_one(self):
        game = Game(7)
        game.grid[0][0] = game.grid[0][1] = "farm"
        game.levels[0][0], game.levels[0][1] = 2, 1
        game.energy = 3
        forecast = game.forecast()
        self.assertEqual(forecast["offline_tiles"], [(0, 0)])
        self.assertEqual((forecast["food"], forecast["energy"]), (4, -3))

    def test_upgrade_round_trip(self):
        game = self.ready_facility("farm")
        game.upgrade(0, 0)
        restored = from_data(to_data(game))
        self.assertEqual(to_data(restored), to_data(game))
        game.next_day()
        restored.next_day()
        self.assertEqual(to_data(restored), to_data(game))

    def test_legacy_migration_does_not_mutate_input(self):
        game = self.ready_facility("farm")
        data = to_data(game)
        data.pop("levels")
        data.pop("happiness")
        data.pop("effects")
        data.pop("last_report")
        [data.pop(key) for key in ("campaign_days", "beacon_stage", "ration_uses", "ration_days", "ruleset", "event_snapshot", "story_seed", "memories", "bulletins_seen", "paused")]
        data["version"] = 1
        original = copy.deepcopy(data)
        restored = from_data(data)
        self.assertEqual(data, original)
        self.assertTrue(restored.imported_from_v1)
        self.assertEqual(restored.levels[0][0], 1)
        self.assertEqual((restored.food, restored.energy, restored.materials),
                         (game.food, game.energy, game.materials))
        self.assertEqual(to_data(restored)["version"], 7)

    def test_invalid_levels_and_impossible_action_budget(self):
        for level in (0, 3, True, -1, "2"):
            game = self.ready_facility("farm")
            data = to_data(game)
            data["levels"][0][0] = level
            with self.assertRaises(SaveError):
                from_data(data)
        game = Game(7)
        game.build(0, 0, "farm")
        data = to_data(game)
        data["levels"][0][0] = 2
        with self.assertRaises(SaveError):
            from_data(data)


if __name__ == "__main__":
    unittest.main()
