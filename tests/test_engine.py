"""Rule tests plus repeatable winning and deliberately neglected colonies."""

import unittest

from engine import BUILDINGS, LEGACY_EVENT_DAYS as EVENT_DAYS, LEGACY_EVENTS, Game, RuleError
from events import EVENTS, describe_option


# Regression fixtures explicitly retain the original 15-day rules.
_CurrentGame = Game
class Game(_CurrentGame):
    def __init__(self, seed=None):
        super().__init__(seed=seed, campaign_days=15)

def safe_choice(game):
    """Prefer the first affordable choice; each free fallback prevents deadlock."""
    game.choose_event(0 if game.option_error(0) is None else 1)


def play_winning_route(seed=7):
    """A concrete opening, then housing expansion. No hidden resource grants."""
    game = Game(seed=seed)
    plan = [(0, "farm"), (1, "mine"), (2, "solar"), (4, "home"),
            (6, "farm"), (7, "solar"), (9, "home")]
    trace = []
    encountered = []
    for _ in range(15):
        if plan and game.day >= plan[0][0] and game.materials >= BUILDINGS[plan[0][1]]["cost"]:
            empty = next((r, c) for r in range(5) for c in range(5) if game.grid[r][c] is None)
            game.build(*empty, plan.pop(0)[1])
        game.next_day()
        if game.pending_event:
            encountered.append(game.pending_event)
            safe_choice(game)
        trace.append((game.day, game.food, game.energy, game.materials, game.population))
    return game, trace, encountered


class EngineTests(unittest.TestCase):
    def test_initial_grid_rows_are_independent(self):
        game = Game(0)
        self.assertEqual(game.grid[2][2], "hq")
        self.assertEqual(sum(tile is None for row in game.grid for tile in row), 24)
        game.grid[0][0] = "solar"
        self.assertIsNone(game.grid[1][0])

    def test_build_cost_and_daily_limit(self):
        game = Game(0)
        game.build(0, 0, "farm")
        self.assertEqual(game.materials, 30)
        with self.assertRaises(RuleError):
            game.build(0, 1, "solar")
        self.assertEqual(game.materials, 30)
        game.next_day()
        game.build(0, 1, "solar")

    def test_invalid_build_is_atomic(self):
        for row, column, kind in [(-1, 0, "farm"), (5, 0, "farm"), (True, 0, "farm"),
                                  (0, 0.5, "farm"), (2, 2, "farm"), (0, 0, "unknown"),
                                  (0, 0, [])]:
            game = Game(0)
            with self.assertRaises(RuleError):
                game.build(row, column, kind)
            self.assertEqual(game.materials, 42)
            self.assertFalse(game.built_today)

    def test_insufficient_materials(self):
        game = Game(0)
        game.materials = 9
        with self.assertRaises(RuleError):
            game.build(0, 0, "solar")
        self.assertIsNone(game.grid[0][0])

    def test_actual_production_values(self):
        game = Game(0)
        game.build(0, 0, "farm")
        game.next_day()
        self.assertEqual((game.food, game.energy, game.materials, game.population), (24, 9, 30, 4))

    def test_farms_have_power_priority(self):
        game = Game(0)
        game.grid[0][0] = "mine"
        game.levels[0][0] = 1
        game.grid[4][4] = "farm"
        game.levels[4][4] = 1
        game.energy = 3
        preview = game.forecast()
        self.assertEqual((preview["farms"], preview["mines"], preview["offline"]), (1, 0, 1))
        game.next_day()
        self.assertEqual((game.food, game.energy, game.materials), (24, 0, 42))

    def test_unpowered_facilities_do_not_produce(self):
        game = Game(0)
        game.grid[0][0] = "farm"
        game.grid[0][1] = "mine"
        game.levels[0][0] = game.levels[0][1] = 1
        game.energy = 0
        game.next_day()
        self.assertEqual((game.food, game.materials), (16, 42))

    def test_forecast_matches_settlement_without_growth(self):
        game = Game(0)
        game.build(0, 0, "farm")
        before = (game.food, game.energy, game.materials)
        forecast = game.forecast()
        game.next_day()
        self.assertEqual(tuple(getattr(game, key) - old for key, old in zip(
            ("food", "energy", "materials"), before)),
            tuple(forecast[key] for key in ("food", "energy", "materials")))

    def test_forecast_reports_starvation_without_negative_food(self):
        game = Game(0)
        game.food = 1
        forecast = game.forecast()
        self.assertEqual((forecast["food"], forecast["food_shortfall"]), (-1, 3))
        game.next_day()
        self.assertEqual((game.food, game.population), (0, 2))

    def test_growth_cost_housing_and_schedule(self):
        game = Game(0)
        game.day = 2
        game.food = 20
        game.next_day()
        self.assertEqual((game.food, game.population), (12, 5))
        game.day = 5
        game.population = 6
        game.food = 40
        game.next_day()
        self.assertEqual(game.population, 6)

    def test_events_are_scheduled_and_unique(self):
        game, _, encountered = play_winning_route()
        self.assertEqual(set(encountered), set(LEGACY_EVENTS))
        self.assertEqual(len(encountered), len(EVENT_DAYS))
        self.assertEqual(game.status, "won")

    def test_same_seed_same_deck(self):
        self.assertEqual(Game(7).event_order, Game(7).event_order)
        self.assertGreater(len({tuple(Game(seed).event_order) for seed in range(10)}), 1)

    def test_pending_event_blocks_turn_and_build(self):
        game = Game(0)
        game.next_day()
        game.next_day()
        with self.assertRaises(RuleError):
            game.next_day()
        with self.assertRaises(RuleError):
            game.build(0, 0, "solar")
        self.assertEqual(game.day, 2)
        safe_choice(game)
        game.build(0, 0, "solar")

    def test_every_event_option_matches_its_data(self):
        for name, event in EVENTS.items():
            for index, option in enumerate(event["options"]):
                with self.subTest(event=name, option=index):
                    game = Game(0)
                    game.population = 4
                    game.food = game.energy = game.materials = 50
                    game.pending_event = name
                    game.choose_event(index)
                    for key in ("food", "energy", "materials", "population", "happiness"):
                        before = 4 if key == "population" else 70 if key == "happiness" else 50
                        expected = before - option.get("cost", {}).get(key, 0) + option.get("change", {}).get(key, 0)
                        self.assertEqual(getattr(game, key), expected)
                    self.assertIsNone(game.pending_event)
                    self.assertTrue(describe_option(option))

    def test_event_cost_rejection_is_atomic(self):
        game = Game(0)
        game.pending_event = "storm"
        game.materials = 0
        with self.assertRaises(RuleError):
            game.choose_event(0)
        self.assertEqual(game.pending_event, "storm")
        self.assertEqual(game.energy, 12)

    def test_all_fallbacks_work_without_resources(self):
        for event in EVENTS:
            game = Game(0)
            game.pending_event = event
            game.food = game.energy = game.materials = 0
            self.assertIsNone(game.option_error(1))
            game.choose_event(1)
            self.assertGreaterEqual(min(game.food, game.energy, game.materials), 0)

    def test_immigration_respects_housing(self):
        game = Game(0)
        game.population = 5
        game.pending_event = "immigrants"
        with self.assertRaises(RuleError):
            game.choose_event(0)
        game.choose_event(1)
        self.assertEqual(game.population, 5)

    def test_invalid_choices(self):
        for index in (-1, 2, True, "1", None):
            game = Game(0)
            game.pending_event = "storm"
            with self.assertRaises(RuleError):
                game.choose_event(index)

    def test_final_departure_can_end_colony(self):
        game = Game(0)
        game.day = 2
        game.population = 1
        game.pending_event = "protest"
        game.choose_event(1)
        self.assertEqual((game.status, game.population), ("lost", 0))

    def test_100_seeds_have_a_winning_route(self):
        for seed in range(100):
            with self.subTest(seed=seed):
                game, trace, _ = play_winning_route(seed)
                self.assertEqual((game.status, game.day), ("won", 15))
                self.assertGreater(game.population, 0)
                self.assertEqual(len(trace), 15)

    def test_doing_nothing_causes_failure(self):
        game = Game(7)
        while game.status == "active":
            game.next_day()
            if game.pending_event:
                game.choose_event(1)
        self.assertEqual((game.status, game.population), ("lost", 0))
        self.assertLess(game.day, 15)
        self.assertEqual(game.result()[0], "Silent Beacon")

    def test_terminal_state_rejects_actions(self):
        game, _, _ = play_winning_route()
        for action in (game.next_day, lambda: game.build(4, 4, "home"), lambda: game.choose_event(0)):
            with self.assertRaises(RuleError):
                action()
        self.assertEqual(game.day, 15)

    def test_rating_thresholds(self):
        game = Game(0)
        game.population = 10
        game.food = game.energy = game.materials = 100
        self.assertEqual(game.result(), ("New Eden", 364))
        game.population = 7
        self.assertEqual(game.result()[0], "Prosperous Colony")
        game.population = 4
        game.food = game.energy = game.materials = 0
        self.assertEqual(game.result()[0], "Struggling Outpost")

    def test_storage_cap_and_log_bound(self):
        game = Game(0)
        game.grid[0][0] = "farm"
        game.grid[0][1] = "mine"
        game.levels[0][0] = game.levels[0][1] = 1
        game.food = game.energy = game.materials = 999
        game.next_day()
        self.assertEqual((game.food, game.energy, game.materials), (995, 993, 999))
        for _ in range(100):
            game._record("test")
        self.assertEqual(len(game.log), 80)


if __name__ == "__main__":
    unittest.main()
