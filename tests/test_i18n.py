"""Localization coverage and live switches must not alter simulation/save state."""

import copy
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from engine import Game
from events import EFFECTS, EVENTS, describe_option
from i18n import CATALOG, EVENT_ZH, translate
from persistence import from_data, load_game, save_game, to_data
from tests.test_strategy import play_v2_route

try:
    import tkinter as tk
except ImportError:
    tk = None


# Regression fixtures explicitly retain the original 15-day rules.
_CurrentGame = Game
class Game(_CurrentGame):
    def __init__(self, seed=None):
        super().__init__(seed=seed, campaign_days=15)

def untranslated_words(text):
    # Brand, file-format names and level identifiers intentionally remain stable.
    cleaned = re.sub(r"COLONY ZERO|Colony Zero|JSON|L[12]|HQ", "", text)
    return re.findall(r"[A-Za-z]{3,}", cleaned)


class CatalogTests(unittest.TestCase):
    def test_english_is_exact_and_default(self):
        for text in ("Build selected facility", "Food  20", "NEXT: DAY 6 (before a new council choice)",
                     "Food +3; Energy -2", "\nUnknown file message\n"):
            self.assertEqual(translate(text), text)
            self.assertEqual(translate(text, "en"), text)

    def test_all_events_choices_and_effects_have_chinese(self):
        self.assertEqual(set(EVENT_ZH), set(EVENTS))
        for event in EVENTS.values():
            for text in (event["title"], event["story"], *(option["label"] for option in event["options"]),
                         *(describe_option(option) for option in event["options"])):
                self.assertFalse(untranslated_words(translate(text, "zh_CN")), text)
        for effect in EFFECTS.values():
            self.assertIn(effect["description"], CATALOG)

    def test_numeric_effects_keep_values_and_signs(self):
        text = "pay 4 Energy; pay 3 Materials; Happiness +2; " + EFFECTS["ore_rush"]["description"]
        localized = translate(text, "zh_CN")
        self.assertIn("支付4能源", localized)
        self.assertIn("支付3材料", localized)
        self.assertIn("+2", localized)
        self.assertIn("3天", localized)
        self.assertIn("4材料", localized)

    def test_legacy_log_formats_translate(self):
        for text in ("Day 4: 1 farm(s), 1 mine(s) powered; Food +8 / -3; Materials +6; Energy reserve 5.",
                     "Community: Happiness +1 -> 71/100.",
                     "New arrival settled: +1 Population, -4 Food for settlement supplies.",
                     "Power shortage: 1 facility/facilities offline (farms have priority).",
                     "Survival crisis: 2 colonist(s) lost; food shortfall 4."):
            self.assertFalse(untranslated_words(translate(text, "zh_CN")), text)

    def test_paths_and_unknown_external_error_details_remain_verbatim(self):
        detail = r"[Errno 2] File missing: C:\Users\Food\Materials\colony.json"
        localized = translate("Could not load colony: " + detail, "zh_CN")
        self.assertEqual(localized, "无法读取殖民地：" + detail)
        self.assertEqual(translate("Saved to Food.json", "zh_CN"), "已保存至 Food.json")

    def test_complete_route_reports_and_logs_have_no_missing_english(self):
        for layout in ("garden", "noisy"):
            snapshots = {}
            play_v2_route(7, layout, snapshots)
            for data in snapshots.values():
                game = from_data(data)
                for text in [*game.log, game.last_report, game.planning_report(), game.summary()]:
                    self.assertFalse(untranslated_words(translate(text, "zh_CN")), text)

    def test_invalid_language_is_rejected(self):
        with self.assertRaises(ValueError):
            translate("Food", "unknown")


class LanguageGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if tk is None:
            raise unittest.SkipTest("Tkinter not available.")
        try:
            cls.root = tk.Tk()
        except tk.TclError as exc:
            raise unittest.SkipTest(f"No display: {exc}")
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

    def test_initial_english_and_switch_round_trip_keep_state(self):
        self.assertEqual(self.app.language, "en")
        self.assertEqual(self.app.language_choice.get(), "English")
        self.app.game.build(0, 0, "farm")
        self.app.game.next_day()
        self.app.selected = (0, 1)
        self.app.feedback = "Last action: Materials -12"
        self.app.refresh()
        game = self.app.game
        before = copy.deepcopy(to_data(game))
        english_text = {name: widget["text"] for name, widget in self.app.metrics.items()}
        self.app.set_language("zh_CN")
        self.assertIs(self.app.game, game)
        self.assertEqual(to_data(game), before)
        self.assertEqual(self.app.selected, (0, 1))
        self.assertIn("食物", self.app.metrics["food"]["text"])
        self.assertIn("材料", self.app.feedback_label["text"])
        self.app.set_language("en")
        self.assertEqual(to_data(game), before)
        self.assertEqual({name: widget["text"] for name, widget in self.app.metrics.items()}, english_text)

    def test_switch_pending_event_and_active_timer_do_not_advance(self):
        self.app.game = Game(7)
        self.app.game.next_day()
        self.app.game.next_day()
        self.app.refresh()
        before = copy.deepcopy(to_data(self.app.game))
        self.app.set_language("zh_CN")
        self.assertIn("议会", self.app.event_title["text"])
        self.assertIn("资助", self.app.event_buttons[0]["text"])
        self.assertEqual(to_data(self.app.game), before)
        self.app.event_buttons[0].invoke()
        before = copy.deepcopy(to_data(self.app.game))
        for language in ("en", "zh_CN", "en", "zh_CN"):
            self.app.set_language(language)
        self.assertEqual(to_data(self.app.game), before)
        self.assertEqual(self.app.game.effects, {"ore_rush": 3})
        self.assertIn("剩余3天", self.app.forecast_label["text"])

    def test_chinese_actions_and_dialogs_still_use_canonical_save(self):
        self.app.set_language("zh_CN")
        self.app.kind.set("farm")
        self.app.refresh()
        self.app.build_button.invoke()
        self.assertEqual(self.app.game.grid[0][0], "farm")
        self.assertIn("材料", self.app.feedback_label["text"])
        self.assertIn("建造", self.app.tr("\n".join(self.app.game.log)))
        self.assertTrue(self.app.game.log[-1].startswith("Build:"))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "colony.json"
            save_game(self.app.game, path)
            restored = load_game(path)
            self.assertEqual(to_data(restored), to_data(self.app.game))
            self.assertEqual(to_data(restored)["version"], 7)
            self.assertNotIn("language", to_data(restored))
            with patch("gui.filedialog.askopenfilename", return_value=str(path)), patch("gui.dialogs.ask_yes_no", return_value=True):
                self.app.load()
        self.assertEqual(self.app.language, "zh_CN")

    def test_localized_report_guide_and_action_error(self):
        self.app.set_language("zh_CN")
        with patch("gui.dialogs.show_info") as info:
            self.app.show_guide()
            self.assertEqual(info.call_args.args[0], "总督指南")
            self.assertFalse(untranslated_words(info.call_args.args[1]))
            self.app.show_report()
            self.assertEqual(info.call_args.args[0], "殖民地周报")
            self.assertFalse(untranslated_words(info.call_args.args[1]))
            self.app.game.materials = 0
            self.app.build()
            self.assertIn("需要10材料", self.app.feedback_label['text'])

    def test_native_dialog_titles_and_filters_follow_language(self):
        self.app.set_language("zh_CN")
        before = copy.deepcopy(to_data(self.app.game))
        with patch("gui.filedialog.asksaveasfilename", return_value="") as dialog:
            self.app.save()
            self.assertEqual(dialog.call_args.kwargs["title"], "保存殖民地")
            self.assertEqual(dialog.call_args.kwargs["filetypes"][0][0], "殖民地JSON存档")
        with patch("gui.filedialog.askopenfilename", return_value="") as dialog:
            self.app.load()
            self.assertEqual(dialog.call_args.kwargs["title"], "读取殖民地")
        self.assertEqual(to_data(self.app.game), before)

    def test_new_game_preserves_current_language(self):
        self.app.set_language("zh_CN")
        with patch("gui.dialogs.ask_yes_no", return_value=True):
            self.app.demo_game()
        self.assertEqual(self.app.language, "zh_CN")
        self.assertEqual(self.app.game.day, 0)
        self.assertIn("新的远征", self.app.feedback_label["text"])

    def test_combobox_event_switches_language(self):
        self.root.deiconify()
        self.root.update()
        self.app.language_choice.set("简体中文")
        self.app.language_selector.event_generate("<<ComboboxSelected>>")
        self.root.update()
        self.assertEqual(self.app.language, "zh_CN")
        self.assertIn("食物", self.app.metrics["food"]["text"])
        self.root.withdraw()

    def test_chinese_minimum_size_keeps_controls_visible(self):
        self.app.set_language("zh_CN")
        self.root.deiconify()
        self.root.geometry("1000x820")
        self.app.game = Game(7)
        self.app.game.next_day()
        self.app.game.next_day()
        self.app.refresh()
        self.root.update()
        for widget in (self.app.language_selector, self.app.next_button, self.app.history_button, *self.app.event_buttons):
            self.assertTrue(widget.winfo_ismapped())
            self.assertGreaterEqual(widget.winfo_height(), widget.winfo_reqheight())
        self.root.withdraw()

    def test_all_visible_catalog_text_and_map_captions_translate(self):
        self.app.set_language("zh_CN")
        for widget in self.app._text_widgets:
            self.assertFalse(untranslated_words(str(widget["text"])), widget.source_text)
        captions = [self.app.board.itemcget(item, "text") for item in self.app.board.find_all()
                    if self.app.board.type(item) == "text"]
        self.assertIn("总部", captions)
        victory, _ = play_v2_route(7)
        failure = Game(7)
        while failure.status == "active":
            failure.next_day()
            if failure.pending_event:
                failure.choose_event(1)
        for game, expected in ((victory, "新伊甸"), (failure, "寂静信标")):
            self.app.game = game
            self.app.refresh()
            self.assertIn(expected, self.app.event_title["text"])
            self.assertFalse(untranslated_words(self.app.event_story["text"]))

    def test_invalid_switch_keeps_language_and_game(self):
        before = copy.deepcopy(to_data(self.app.game))
        with self.assertRaises(ValueError):
            self.app.set_language("invalid")
        self.assertEqual(self.app.language, "en")
        self.assertEqual(to_data(self.app.game), before)


if __name__ == "__main__":
    unittest.main()
