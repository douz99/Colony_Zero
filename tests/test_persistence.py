"""Save round trips, malformed input and write-failure recovery."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from engine import Game
from persistence import SaveError, from_data, load_game, save_game, to_data
from tests.test_engine import play_winning_route, safe_choice


# Regression fixtures explicitly retain the original 15-day rules.
_CurrentGame = Game
class Game(_CurrentGame):
    def __init__(self, seed=None):
        super().__init__(seed=seed, campaign_days=15)

class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "colony.json"

    def test_new_game_round_trip(self):
        game = Game(7)
        save_game(game, self.path)
        self.assertEqual(to_data(load_game(self.path)), to_data(game))

    def test_successful_overwrite_replaces_the_saved_game(self):
        save_game(Game(7), self.path)
        game = Game(8)
        game.build(0, 0, "farm")
        game.next_day()
        save_game(game, self.path)
        self.assertEqual(to_data(load_game(self.path)), to_data(game))

    def test_pending_choice_and_future_events_are_preserved(self):
        game = Game(7)
        game.build(0, 0, "farm")
        game.next_day()
        game.build(0, 1, "mine")
        game.next_day()
        save_game(game, self.path)
        restored = load_game(self.path)
        self.assertEqual(restored.pending_event, "deposit")
        safe_choice(game)
        safe_choice(restored)
        game.build(0, 2, "solar")
        restored.build(0, 2, "solar")
        for _ in range(13):
            game.next_day()
            restored.next_day()
            if game.pending_event:
                safe_choice(game)
                safe_choice(restored)
            self.assertEqual(to_data(game), to_data(restored))

    def test_winning_ending_round_trip(self):
        game, _, _ = play_winning_route()
        save_game(game, self.path)
        self.assertEqual(to_data(load_game(self.path)), to_data(game))

    def test_losing_ending_round_trip(self):
        game = Game(7)
        while game.status == "active":
            game.next_day()
            if game.pending_event:
                game.choose_event(1)
        save_game(game, self.path)
        self.assertEqual(to_data(load_game(self.path)), to_data(game))

    def test_read_missing_file(self):
        with self.assertRaises(SaveError):
            load_game(self.path)

    def test_invalid_json_and_encoding(self):
        for content in (b'{"food":', b'null', b'[]', b'\xff\xfe', b'{"x": NaN}'):
            self.path.write_bytes(content)
            with self.assertRaises(SaveError):
                load_game(self.path)

    def test_oversized_and_deep_json(self):
        for content in (" " * 100001, "[" * 2000 + "]" * 2000):
            self.path.write_text(content, encoding="utf-8")
            with self.assertRaises(SaveError):
                load_game(self.path)

    def test_bad_field_values(self):
        cases = [("version", 8), ("version", True), ("food", -1), ("food", True),
                 ("energy", 1.5), ("materials", 1000), ("population", 200),
                 ("population", 0), ("population", 7), ("day", 16), ("day", True),
                 ("built_today", 1), ("built_today", True), ("status", []),
                 ("status", "won"), ("status", "lost"), ("reason", "unexpected"),
                 ("pending_event", "storm"), ("pending_event", []),
                 ("log", []), ("log", [123]), ("log", ["x" * 501]),
                 ("event_order", ["storm"] * 6), ("event_order", [1, 2, 3, 4, 5, 6]),
                 ("grid", []), ("grid", [[[]] * 5] * 5)]
        for field, value in cases:
            with self.subTest(field=field, value=str(value)[:30]):
                data = to_data(Game(7))
                data[field] = value
                with self.assertRaises(SaveError):
                    from_data(data)

    def test_bad_map_hq_and_construction_count(self):
        for row, column, tile in ((2, 2, None), (0, 0, "hq"), (0, 0, "castle"), (0, 0, "farm")):
            data = to_data(Game(7))
            data["grid"][row][column] = tile
            with self.assertRaises(SaveError):
                from_data(data)

    def test_missing_and_extra_fields(self):
        data = to_data(Game(7))
        data.pop("food")
        with self.assertRaises(SaveError):
            from_data(data)
        data = to_data(Game(7))
        data["cheat"] = True
        with self.assertRaises(SaveError):
            from_data(data)

    def test_event_must_match_date_and_deck(self):
        data = to_data(Game(7))
        data["day"] = 2
        data["pending_event"] = "storm"
        with self.assertRaises(SaveError):
            from_data(data)

    def test_loaded_containers_do_not_alias_input(self):
        data = to_data(Game(7))
        restored = from_data(data)
        data["grid"][0][0] = "farm"
        self.assertIsNone(restored.grid[0][0])

    def test_failed_replace_preserves_existing_save_and_cleans_temp(self):
        save_game(Game(7), self.path)
        original = self.path.read_bytes()
        with patch("persistence.os.replace", side_effect=PermissionError("simulated locked file")):
            with self.assertRaises(SaveError):
                save_game(Game(8), self.path)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.glob(".colony-*.tmp")), [])

    def test_unwritable_missing_folder(self):
        with self.assertRaises(SaveError):
            save_game(Game(7), self.path.parent / "missing" / "save.json")

    def test_active_effect_round_trip_and_countdown(self):
        game = Game(7)
        game.next_day()
        game.next_day()
        game.choose_event(0)
        save_game(game, self.path)
        restored = load_game(self.path)
        self.assertEqual(restored.effects, {"ore_rush": 3})
        game.next_day()
        restored.next_day()
        self.assertEqual(to_data(restored), to_data(game))
        self.assertEqual(restored.effects, {"ore_rush": 2})

    def test_transient_file_lock_is_retried_without_losing_old_save(self):
        import os
        save_game(Game(7), self.path)
        original_replace = os.replace
        calls = []
        def briefly_locked(source, target):
            calls.append(target)
            if len(calls) == 1:
                raise PermissionError("simulated short desktop lock")
            original_replace(source, target)
        with patch("persistence.os.replace", side_effect=briefly_locked):
            save_game(Game(8), self.path)
        self.assertEqual(len(calls), 2)
        self.assertEqual(load_game(self.path).event_order, Game(8).event_order)


if __name__ == "__main__":
    unittest.main()
