"""Real Tk widget smoke tests. Dialogs are mocked to avoid blocking input."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    import tkinter as tk
except ImportError:
    tk = None

from engine import Game
from persistence import save_game, to_data
from tests.test_engine import play_winning_route


# Regression fixtures explicitly retain the original 15-day rules.
_CurrentGame = Game
class Game(_CurrentGame):
    def __init__(self, seed=None):
        super().__init__(seed=seed, campaign_days=15)

class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if tk is None:
            raise unittest.SkipTest("Tkinter is not installed; engine tests still run.")
        try:
            cls.root = tk.Tk()
        except tk.TclError as exc:
            raise unittest.SkipTest(f"No graphical display: {exc}")
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        from gui import ColonyApp
        for widget in self.root.winfo_children():
            widget.destroy()
        self.app = ColonyApp(self.root)
        self.app.ration_explained = True
        self.addCleanup(self.app._cancel_effects)
        self.root.update_idletasks()

    def test_build_advance_and_pending_decision_buttons(self):
        self.app.game = Game(7)
        self.app.kind.set("farm")
        self.app.refresh()
        self.app.build_button.invoke()
        self.assertEqual(self.app.game.grid[0][0], "farm")
        self.assertEqual(str(self.app.build_button["state"]), "disabled")
        self.app.next_button.invoke()
        self.app.next_button.invoke()
        self.assertEqual(self.app.game.pending_event, "deposit")
        self.assertEqual(str(self.app.next_button["state"]), "disabled")
        self.app.event_buttons[1].invoke()
        self.assertIsNone(self.app.game.pending_event)
        self.assertEqual(str(self.app.next_button["state"]), "normal")

    def test_cancelled_save_load_leave_game_unchanged(self):
        before = to_data(self.app.game)
        with patch("gui.filedialog.asksaveasfilename", return_value=""), patch("gui.filedialog.askopenfilename", return_value=""):
            self.app.save()
            self.app.load()
        self.assertEqual(to_data(self.app.game), before)

    def test_corrupt_load_keeps_current_game(self):
        before = to_data(self.app.game)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "broken.json"
            path.write_text("broken", encoding="utf-8")
            with patch("gui.filedialog.askopenfilename", return_value=str(path)), patch("gui.dialogs.show_info") as error:
                self.app.load()
                error.assert_called_once()
        self.assertEqual(to_data(self.app.game), before)

    def test_valid_load_accept_and_decline(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "valid.json"
            game = Game(7)
            game.build(0, 0, "farm")
            game.next_day()
            save_game(game, path)
            before = to_data(self.app.game)
            with patch("gui.filedialog.askopenfilename", return_value=str(path)), patch("gui.dialogs.ask_yes_no", return_value=False):
                self.app.load()
            self.assertEqual(to_data(self.app.game), before)
            with patch("gui.filedialog.askopenfilename", return_value=str(path)), patch("gui.dialogs.ask_yes_no", return_value=True):
                self.app.load()
            self.assertEqual(to_data(self.app.game), to_data(game))

    def test_save_callback_writes_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "saved.json"
            with patch("gui.filedialog.asksaveasfilename", return_value=str(path)), patch("gui.dialogs.show_info"):
                self.app.save()
            self.assertTrue(path.is_file())

    def test_new_and_demo_cancel_or_restart(self):
        self.app.game.day = 1
        with patch("gui.dialogs.ask_yes_no", return_value=False):
            self.app.new_game()
        self.assertEqual(self.app.game.day, 1)
        with patch("gui.dialogs.ask_yes_no", return_value=True):
            self.app.demo_game()
        self.assertEqual(self.app.game.day, 0)
        self.assertEqual(self.app.game.event_order, _CurrentGame(7).event_order)

    def test_end_screen_disables_actions(self):
        self.app.game, _, _ = play_winning_route()
        self.app.refresh()
        self.assertIn("New Eden", self.app.event_title["text"])
        self.assertEqual(str(self.app.next_button["state"]), "disabled")
        self.assertEqual(str(self.app.build_button["state"]), "disabled")

    def test_upgrade_button_and_actual_delta_feedback(self):
        self.app.game = Game(7)
        self.app.kind.set("solar")
        self.app.refresh()
        self.app.build_button.invoke()
        self.assertIn("Materials -10", self.app.feedback)
        self.assertEqual(str(self.app.upgrade_button["state"]), "disabled")
        self.app.next_button.invoke()
        self.app.upgrade_button.invoke()
        self.assertEqual(self.app.game.levels[0][0], 2)
        self.assertIn("Materials -8", self.app.feedback)
        self.assertIn("Maximum level", self.app.upgrade_button["text"])
        self.assertEqual(str(self.app.build_button["state"]), "disabled")

    def test_happiness_bar_and_keyboard_map_selection(self):
        self.app.game.happiness = 29
        self.app.refresh()
        self.assertIn("29/100", self.app.happiness_label["text"])
        self.assertTrue(self.app.happiness_bar.find_all())
        self.app._move_selection(0, 1)
        self.assertEqual(self.app.selected, (0, 1))
        self.app._move_selection(-1, 0)
        self.assertEqual(self.app.selected, (0, 1))

    def test_vector_map_draws_all_types_levels_and_offline_caption(self):
        self.root.deiconify()
        self.app.game = Game(7)
        for c, kind in enumerate(("solar", "farm", "mine", "home")):
            self.app.game.grid[0][c] = kind
            self.app.game.levels[0][c] = 2
        self.app.game.energy = 0
        self.app.game.grid[0][0] = None
        self.app.game.levels[0][0] = 0
        self.app.refresh()
        self.root.update()
        texts = [self.app.board.itemcget(item, "text") for item in self.app.board.find_all()
                 if self.app.board.type(item) == "text"]
        self.assertIn("NEXT: OFFLINE", texts)
        self.assertIn("L2", texts)
        self.assertIn("HQ", texts)
        self.root.withdraw()

    def test_legacy_import_confirmation_is_explicit(self):
        import json
        data = to_data(Game(7))
        data.pop("levels")
        data.pop("happiness")
        data.pop("effects")
        data.pop("last_report")
        [data.pop(key) for key in ("campaign_days", "beacon_stage", "ration_uses", "ration_days", "ruleset", "event_snapshot", "story_seed", "memories", "bulletins_seen", "paused")]
        data["version"] = 1
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "v1.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with patch("gui.filedialog.askopenfilename", return_value=str(path)), patch("gui.dialogs.ask_yes_no", return_value=True) as confirm:
                self.app.load()
            self.assertIn("Happiness at 70", confirm.call_args.args[1])
            self.assertTrue(self.app.game.imported_from_v1)

    def test_minimum_size_keeps_history_and_both_event_choices_visible(self):
        self.root.deiconify()
        self.root.geometry("1000x820")
        self.app.game = Game(7)
        self.app.game.next_day()
        self.app.game.next_day()
        self.app.refresh()
        self.root.update()
        for widget in (self.app.history_button, self.app.next_button, *self.app.event_buttons):
            self.assertTrue(widget.winfo_ismapped())
            self.assertGreaterEqual(widget.winfo_height(), widget.winfo_reqheight())
            self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(),
                                 self.root.winfo_rooty() + self.root.winfo_height())
        self.root.withdraw()

    def test_minimum_size_keeps_construction_and_history_visible(self):
        self.root.deiconify()
        self.root.geometry("1000x820")
        self.app.game = Game(7)
        self.app.game.build(0, 0, "farm")
        self.app.game.next_day()
        self.app.refresh()
        self.root.update()
        for widget in (self.app.history_button, self.app.build_button, self.app.upgrade_button, self.app.event_story):
            self.assertTrue(widget.winfo_ismapped())
            self.assertGreaterEqual(widget.winfo_height(), widget.winfo_reqheight())
        self.root.withdraw()

    def test_report_and_guide_use_engine_facts(self):
        self.app.game = Game(7)
        self.app.game.build(0, 0, "farm")
        self.app.game.next_day()
        self.app.refresh()
        with patch("gui.dialogs.show_info") as info:
            self.app.show_report()
            self.assertIn("SETTLED: DAY 1", info.call_args.args[1])
            self.assertIn("NEXT: DAY 2", info.call_args.args[1])
            self.app.show_guide()
            self.assertIn("1 Food/day", info.call_args.args[1])

    def test_site_preview_and_effect_summary_visible(self):
        self.app.game = Game(7)
        self.app.game.grid[1][0] = "home"
        self.app.game.levels[1][0] = 1
        self.app.kind.set("farm")
        self.app.refresh()
        self.assertIn("+2 Food", self.app.site_hint["text"])
        self.app.game.effects = {"solar_storm": 2}
        self.app.refresh()
        self.assertIn("Solar 50%", self.app.forecast_label["text"])


if __name__ == "__main__":
    unittest.main()
