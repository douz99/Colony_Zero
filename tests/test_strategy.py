"""V2.0 placement, timed decisions and exact forecast/settlement agreement."""

import copy
import unittest

from engine import BUILDINGS, Game, UPGRADE_COSTS
from events import EVENTS, describe_option
from persistence import SaveError, from_data, to_data
from tests.test_engine import safe_choice


# Regression fixtures explicitly retain the original 15-day rules.
_CurrentGame = Game
class Game(_CurrentGame):
    def __init__(self, seed=None):
        super().__init__(seed=seed, campaign_days=15)

def play_v2_route(seed=7, layout="garden", snapshots=None):
    """A normal adaptable plan; compare two layouts without extra resources."""
    sites = {"farm": (0, 0), "mine": (0, 2), "solar": (4, 4),
             "home": (1, 0) if layout == "garden" else (0, 1),
             "home2": (2, 0) if layout == "garden" else (1, 2),
             "farm2": (2, 1) if layout == "garden" else (0, 3)}
    plan = [(0, "build", "farm"), (1, "build", "mine"), (2, "build", "solar"),
            (3, "upgrade", "solar"), (4, "build", "home"), (6, "upgrade", "farm"),
            (7, "upgrade", "mine"), (8, "upgrade", "home"), (10, "build", "home2"),
            (11, "build", "farm2")]
    game = Game(seed)
    trace = []
    for _ in range(15):
        if plan and game.day >= plan[0][0]:
            _, action, site = plan[0]
            kind = site.rstrip("2")
            cost = BUILDINGS[kind]["cost"] if action == "build" else UPGRADE_COSTS[kind]
            if game.materials >= cost:
                getattr(game, action)(*sites[site], *([kind] if action == "build" else []))
                plan.pop(0)
        before = {key: getattr(game, key) for key in ("food", "energy", "materials", "population", "happiness")}
        forecast = game.forecast()
        game.next_day()
        for key, old in before.items():
            if getattr(game, key) - old != forecast[key]:
                raise AssertionError(f"Forecast mismatch: {key}, Day {game.day}")
        if snapshots is not None:
            snapshots[(game.day, "before_choice")] = copy.deepcopy(to_data(game))
        if game.pending_event:
            safe_choice(game)
        if snapshots is not None:
            snapshots[(game.day, "after_choice")] = copy.deepcopy(to_data(game))
        trace.append((game.day, game.food, game.energy, game.materials, game.population, game.happiness))
    return game, trace


class StrategyTests(unittest.TestCase):
    def add(self, game, row, column, kind, level=1):
        # Focused rule fixtures; full-route tests below use only legal actions.
        game.grid[row][column] = kind
        game.levels[row][column] = level

    def storm_state(self, reserve):
        game = Game(7)
        game.day = 4
        game.pending_event = "storm"
        game.energy = reserve
        game.food = 80
        self.add(game, 0, 0, "farm")
        self.add(game, 0, 2, "mine")
        self.add(game, 4, 4, "solar")
        return game

    def test_food_demand_and_home_power_create_visible_pressure(self):
        game = Game(7)
        self.add(game, 0, 0, "farm")
        self.add(game, 4, 4, "home")
        game.energy = 3
        forecast = game.forecast()
        self.assertEqual(game.food_demand, 4)
        self.assertEqual(forecast["home_power"], 1)
        self.assertEqual(forecast["farms"], 0)
        self.assertEqual(forecast["offline_tiles"], [(0, 0)])
        self.assertEqual((forecast["food"], forecast["energy"]), (-4, -1))

    def test_unpowered_housing_pauses_growth(self):
        game = Game(7)
        self.add(game, 4, 4, "home")
        game.day = 2
        game.energy = 0
        forecast = game.forecast()
        self.assertFalse(forecast["growth"])
        self.assertIn("unpowered housing", forecast["growth_reason"])
        game.next_day()
        self.assertEqual(game.population, 4)

    def test_orthogonal_food_link_and_no_stacking(self):
        game = Game(7)
        self.add(game, 0, 0, "farm")
        self.add(game, 1, 1, "home")
        self.assertEqual(game.forecast()["farm_bonus"], 0)
        self.add(game, 1, 0, "home")
        self.add(game, 0, 1, "home")
        self.assertEqual(game.forecast()["farm_bonus"], 2)
        self.assertEqual(game._production()["food"], 10)

    def test_unpowered_farm_has_no_food_bonus(self):
        game = Game(7)
        self.add(game, 0, 0, "farm")
        self.add(game, 1, 0, "home")
        game.energy = 0
        self.assertEqual(game.forecast()["farm_bonus"], 0)

    def test_noise_counts_homes_once_and_caps_at_four(self):
        game = Game(7)
        game.energy = 30
        self.add(game, 1, 1, "mine")
        self.add(game, 0, 1, "home")
        self.add(game, 0, 0, "mine")
        self.assertEqual(game.pollution(), 2)
        self.add(game, 1, 0, "home")
        self.add(game, 1, 2, "home")
        self.assertEqual(game.pollution(), 4)
        self.assertEqual(game.forecast()["happiness"], -4)

    def test_neighbors_do_not_wrap_at_map_edges(self):
        self.assertEqual(set(Game.neighbors(0, 0)), {(1, 0), (0, 1)})
        game = Game(7)
        self.add(game, 0, 0, "farm")
        self.add(game, 4, 0, "home")
        self.assertEqual(game.forecast()["farm_bonus"], 0)

    def test_storm_applies_to_exactly_next_two_settlements(self):
        game = self.storm_state(30)
        game.choose_event(1)
        self.assertEqual(game.effects, {"solar_storm": 2})
        self.assertEqual(game.forecast()["solar"], 3)
        game.next_day()
        self.assertEqual(game.effects, {"solar_storm": 1})
        self.assertIn("Solar +3", game.last_report)
        game.next_day()
        self.assertEqual(game.effects, {})
        self.assertEqual(game.forecast()["solar"], 7)
        self.assertIn("Effect ended", "\n".join(game.log))

    def test_shielding_is_valuable_when_reserves_are_low(self):
        shield = self.storm_state(0)
        ride = copy.deepcopy(shield)
        shield.choose_event(0)
        ride.choose_event(1)
        for _ in range(2):
            shield.next_day()
            ride.next_day()
        self.assertGreater(shield.materials, ride.materials)

    def test_riding_storm_preserves_materials_with_large_reserve(self):
        shield = self.storm_state(30)
        ride = copy.deepcopy(shield)
        shield.choose_event(0)
        ride.choose_event(1)
        for _ in range(2):
            shield.next_day()
            ride.next_day()
        self.assertEqual(ride.materials - shield.materials, 8)

    def ore_state(self, day):
        seed = 7 if day == 2 else next(seed for seed in range(100) if Game(seed).event_order[-1] == "deposit")
        game = Game(seed)
        game.day = day
        game.pending_event = "deposit"
        game.energy = 30
        game.food = 80
        self.add(game, 0, 2, "mine")
        return game

    def test_ore_investment_wins_over_immediate_fragments_early(self):
        invest = self.ore_state(2)
        collect = copy.deepcopy(invest)
        invest.choose_event(0)
        collect.choose_event(1)
        for _ in range(3):
            invest.next_day()
            collect.next_day()
            if invest.pending_event:
                invest.choose_event(0)
                collect.choose_event(0)
        self.assertEqual(invest.materials - collect.materials, 4)
        self.assertNotIn("ore_rush", invest.effects)

    def test_immediate_fragments_win_on_day_fourteen(self):
        invest = self.ore_state(14)
        collect = copy.deepcopy(invest)
        invest.choose_event(0)
        collect.choose_event(1)
        invest.next_day()
        collect.next_day()
        self.assertEqual(collect.materials - invest.materials, 4)
        self.assertEqual(invest.effects["ore_rush"], 2)
        self.assertEqual(invest.status, "won")

    def test_ore_bonus_requires_a_powered_mine(self):
        game = self.ore_state(2)
        game.choose_event(0)
        game.energy = 0
        self.assertEqual(game.forecast()["ore_bonus"], 0)
        self.assertEqual(game.forecast()["materials"], 0)

    def test_effect_and_report_survive_save_load_without_extra_day(self):
        game = self.storm_state(30)
        game.choose_event(1)
        game.next_day()
        loaded = from_data(to_data(game))
        self.assertEqual(loaded.effects, {"solar_storm": 1})
        self.assertEqual(loaded.last_report, game.last_report)
        self.assertEqual(loaded.forecast(), game.forecast())
        before = copy.deepcopy(to_data(loaded))
        loaded.forecast()
        loaded.planning_report()
        self.assertEqual(to_data(loaded), before)
        loaded.next_day()
        game.next_day()
        self.assertEqual(to_data(loaded), to_data(game))

    def test_effect_and_report_validation(self):
        for effects in ({"unknown": 2}, {"solar_storm": 0}, {"solar_storm": True},
                        {"ore_rush": 4}, {"solar_storm": 2}, []):
            data = to_data(Game(7))
            data["effects"] = effects
            with self.assertRaises(SaveError):
                from_data(data)
        data = to_data(Game(7))
        data["last_report"] = ["not text"]
        with self.assertRaises(SaveError):
            from_data(data)

    def test_stale_effect_counter_is_rejected(self):
        game = self.storm_state(30)
        game.choose_event(1)
        game.next_day()
        data = to_data(game)
        data["effects"]["solar_storm"] = 2
        with self.assertRaises(SaveError):
            from_data(data)

    def test_schema_two_import_preserves_progress_and_adds_no_effects(self):
        game = Game(7)
        game.build(0, 0, "farm")
        game.next_day()
        data = to_data(game)
        data.pop("effects")
        data.pop("last_report")
        [data.pop(key) for key in ("campaign_days", "beacon_stage", "ration_uses", "ration_days", "ruleset", "event_snapshot", "story_seed", "memories", "bulletins_seen", "paused")]
        data["version"] = 2
        before = copy.deepcopy(data)
        migrated = from_data(data)
        self.assertEqual(migrated.imported_from_version, 2)
        self.assertEqual(migrated.effects, {})
        self.assertEqual(migrated.food, game.food)
        self.assertEqual(data, before)

    def test_all_new_effects_are_explained_before_selection(self):
        self.assertIn("next 2 days", describe_option(EVENTS["storm"]["options"][1]))
        self.assertIn("next 3 days", describe_option(EVENTS["deposit"]["options"][0]))

    def test_full_forecast_includes_growth(self):
        game = Game(7)
        game.day = 2
        forecast = game.forecast()
        self.assertEqual((forecast["food"], forecast["population"]), (-8, 1))
        game.next_day()
        self.assertEqual((game.food, game.population), (12, 5))

    def test_one_hundred_seeds_with_forecast_parity_and_good_layout(self):
        for seed in range(100):
            with self.subTest(seed=seed):
                game, trace = play_v2_route(seed)
                self.assertEqual((game.status, game.day), ("won", 15))
                self.assertEqual(len(trace), 15)

    def test_placement_changes_the_same_plan_outcome(self):
        garden, _ = play_v2_route(7, "garden")
        noisy, _ = play_v2_route(7, "noisy")
        self.assertGreater(garden.happiness, noisy.happiness)
        self.assertGreater(garden.food, noisy.food)
        self.assertEqual(garden.result()[0], "New Eden")
        self.assertNotEqual(noisy.result()[0], "New Eden")


if __name__ == "__main__":
    unittest.main()
