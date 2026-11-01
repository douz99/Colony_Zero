"""Happiness rules and complete expeditions using the new upgrade choices."""

import unittest

from engine import BUILDINGS, Game, RuleError, UPGRADE_COSTS
from events import EVENTS
from persistence import SaveError, from_data, to_data
from tests.test_engine import safe_choice


# Regression fixtures explicitly retain the original 15-day rules.
_CurrentGame = Game
class Game(_CurrentGame):
    def __init__(self, seed=None):
        super().__init__(seed=seed, campaign_days=15)

def play_upgrade_route(seed=7, snapshots=None):
    """Use all four L2 types, delaying construction if events reduce materials."""
    plan = [(0, "build", "farm"), (1, "build", "mine"), (2, "build", "solar"),
            (3, "upgrade", "solar"), (4, "build", "home"), (6, "upgrade", "farm"),
            (7, "upgrade", "mine"), (8, "upgrade", "home"), (10, "build", "home"),
            (11, "build", "farm")]
    game = Game(seed)
    trace = []
    for _ in range(15):
        if plan and game.day >= plan[0][0]:
            earliest, action, kind = plan[0]
            cost = BUILDINGS[kind]["cost"] if action == "build" else UPGRADE_COSTS[kind]
            if game.materials >= cost:
                if action == "build":
                    location = next((r, c) for r in range(5) for c in range(5) if game.grid[r][c] is None)
                    game.build(*location, kind)
                else:
                    location = next((r, c) for r in range(5) for c in range(5)
                                    if game.grid[r][c] == kind and game.levels[r][c] == 1)
                    game.upgrade(*location)
                plan.pop(0)
        game.next_day()
        if snapshots is not None:
            snapshots[(game.day, "before_choice")] = to_data(from_data(to_data(game)))
        if game.pending_event:
            safe_choice(game)
        if snapshots is not None:
            snapshots[(game.day, "after_choice")] = to_data(from_data(to_data(game)))
        trace.append((game.day, game.food, game.energy, game.materials, game.population, game.happiness))
    return game, trace


class CommunityTests(unittest.TestCase):
    def test_healthy_day_recovers_one_point(self):
        game = Game(7)
        game.next_day()
        self.assertEqual(game.happiness, 71)

    def test_crowding_costs_two_points(self):
        game = Game(7)
        game.population = 6
        game.next_day()
        self.assertEqual(game.happiness, 68)

    def test_starvation_and_offline_penalties_add(self):
        game = Game(7)
        game.build(0, 0, "farm")
        game.energy = game.food = 0
        game.next_day()
        self.assertEqual((game.happiness, game.population), (57, 2))

    def test_low_happiness_pauses_growth_without_reducing_production(self):
        game = Game(7)
        game.build(0, 0, "farm")
        game.day = 2
        game.happiness = 10
        game.next_day()
        self.assertEqual((game.population, game.food, game.happiness), (4, 24, 11))
        self.assertIn("Growth paused", "\n".join(game.log))

    def test_recovery_to_threshold_allows_growth_same_day(self):
        game = Game(7)
        game.day = 2
        game.happiness = 39
        game.next_day()
        self.assertEqual((game.population, game.happiness), (5, 40))

    def test_happiness_caps_and_event_effects_are_visible(self):
        from events import describe_option
        for event in EVENTS.values():
            for option in event["options"]:
                self.assertIn("Happiness", describe_option(option))
        game = Game(7)
        game.pending_event = "protest"
        game.happiness = 99
        game.choose_event(0)
        self.assertEqual(game.happiness, 100)
        game.pending_event = "protest"
        game.happiness = 2
        game.choose_event(1)
        self.assertEqual(game.happiness, 0)

    def test_happiness_gates_rating(self):
        game = Game(7)
        game.population = 10
        game.food = game.energy = game.materials = 100
        game.happiness = 64
        self.assertEqual(game.result()[0], "Prosperous Colony")
        game.happiness = 65
        self.assertEqual(game.result()[0], "New Eden")
        game.happiness = 39
        self.assertEqual(game.result()[0], "Struggling Outpost")

    def test_happiness_round_trip_and_invalid_inputs(self):
        game = Game(7)
        game.happiness = 17
        self.assertEqual(from_data(to_data(game)).happiness, 17)
        for invalid in (-1, 101, True, 70.0, "70", None):
            data = to_data(Game(7))
            data["happiness"] = invalid
            with self.assertRaises(SaveError):
                from_data(data)

    def test_100_seeds_survive_with_upgrade_strategy(self):
        for seed in range(100):
            with self.subTest(seed=seed):
                game, trace = play_upgrade_route(seed)
                self.assertEqual((game.status, game.day), ("won", 15))
                self.assertEqual(len(trace), 15)

    def test_demo_uses_all_four_upgrades_and_has_summary(self):
        game, _ = play_upgrade_route(7)
        self.assertEqual(game.upgrade_count, 4)
        self.assertEqual({game.grid[r][c] for r in range(5) for c in range(5)
                          if game.levels[r][c] == 2}, set(BUILDINGS))
        self.assertIn("4 L2 upgrades", game.summary())
        self.assertEqual(game.result()[0], "New Eden")
        with self.assertRaises(RuleError):
            game.upgrade(0, 0)


if __name__ == "__main__":
    unittest.main()
