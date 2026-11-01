"""Real Tk controls for HQ work, emergency orders and bilingual layout."""
import copy
import unittest
from unittest.mock import patch

try:
    import tkinter as tk
except ImportError:
    tk = None

from engine import Game
from persistence import from_data, to_data
from tests.test_expedition import play_expedition
from tests.test_i18n import untranslated_words


class ExpeditionGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if tk is None:
            raise unittest.SkipTest("Tkinter unavailable.")
        try:
            cls.root = tk.Tk()
        except tk.TclError as exc:
            raise unittest.SkipTest(f"No display: {exc}")
        cls.root.withdraw()
        cls.snapshots = {}
        play_expedition(snapshots=cls.snapshots)

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

    def test_new_games_default_to_thirty_days_eight_events(self):
        self.assertEqual(self.app.language, "en")
        self.assertEqual(self.app.day_label["text"], "Week 00 / 30")
        with patch("gui.dialogs.ask_yes_no", return_value=True):
            self.app.demo_game()
        self.assertEqual(len(self.app.game.event_order), 12)
        self.assertEqual(self.app.game.event_order[0], "medical")

    def test_beacon_button_pays_and_shares_crew(self):
        self.app.game = from_data(copy.deepcopy(self.snapshots[(8, "after_choice")]))
        self.app.refresh()
        self.assertEqual(str(self.app.beacon_button["state"]), "normal")
        self.app.beacon_button.invoke()
        self.assertEqual(self.app.game.beacon_stage, 1)
        self.assertEqual(str(self.app.build_button["state"]), "disabled")
        self.assertIn("Beacon 1/3", self.app.mission_label["text"])
        self.assertIn("Materials -18", self.app.feedback_label["text"])

    def test_ration_control_and_language_switch_keep_state(self):
        self.app.ration_button.invoke()
        self.assertEqual(self.app.game.ration_uses, 1)
        self.assertEqual(str(self.app.ration_button["state"]), "disabled")
        before = copy.deepcopy(to_data(self.app.game))
        self.app.set_language("zh_CN")
        self.assertEqual(to_data(self.app.game), before)
        self.assertIn("剩1次", self.app.ration_button["text"])
        self.assertIn("口粮", self.app.forecast_label["text"])
        self.assertIn("信标", self.app.mission_label["text"])

    def test_all_eight_councils_visible_and_translated(self):
        self.root.deiconify()
        self.root.geometry("1040x880")
        for day in (2, 5, 9, 13, 17, 21, 25, 28):
            self.app.game = from_data(copy.deepcopy(self.snapshots[(day, "before_choice")]))
            for language in ("en", "zh_CN"):
                self.app.set_language(language)
                self.root.update()
                for widget in (*self.app.event_buttons, self.app.event_story, self.app.next_button,
                               self.app.beacon_button, self.app.ration_button):
                    self.assertTrue(widget.winfo_ismapped(), (day, language, widget))
                    self.assertGreaterEqual(widget.winfo_height(), widget.winfo_reqheight(), (day, language, widget))
                    self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), self.root.winfo_rooty() + self.root.winfo_height())
                self.assertEqual(str(self.app.beacon_button["state"]), "disabled")
                self.assertEqual(str(self.app.ration_button["state"]), "disabled")
                if language == "zh_CN":
                    for widget in (self.app.event_title, self.app.event_story, *self.app.event_buttons):
                        self.assertFalse(untranslated_words(widget["text"]), widget["text"])
        self.root.withdraw()

    def test_construction_and_mission_visible_at_minimum_size(self):
        self.root.deiconify()
        self.root.geometry("1040x880")
        for language in ("en", "zh_CN"):
            self.app.set_language(language)
            self.root.update()
            for widget in (self.app.board, self.app.build_button, self.app.upgrade_button,
                           self.app.beacon_button, self.app.ration_button, self.app.event_story):
                self.assertTrue(widget.winfo_ismapped())
                self.assertGreaterEqual(widget.winfo_height(), 30 if widget is self.app.board else widget.winfo_reqheight())
        self.root.withdraw()

    def test_population_icons_reflect_people(self):
        self.app.refresh()
        self.assertEqual(len(self.app.crew_icons.find_all()), self.app.game.population * 2)

    def test_both_endings_disable_new_controls_and_show_correct_reason(self):
        for objective in (True, False):
            game, _ = play_expedition(objective=objective)
            self.app.game = game
            self.app.set_language("zh_CN")
            self.assertEqual(str(self.app.beacon_button["state"]), "disabled")
            self.assertEqual(str(self.app.ration_button["state"]), "disabled")
            self.assertFalse(untranslated_words(self.app.event_story["text"]), self.app.event_story["text"])
            self.assertIn("获救" if objective else "失联", self.app.event_story["text"])


if __name__ == "__main__":
    unittest.main()
