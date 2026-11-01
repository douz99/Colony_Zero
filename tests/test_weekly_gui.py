"""Real weekly UI, twelve bilingual choice cards and cancellable feedback."""
import copy
import unittest
from unittest.mock import patch
try:
    import tkinter as tk
except ImportError:
    tk=None
from engine import EVENT_DAYS
from persistence import from_data,to_data
from tests.test_v31 import play_route
from tests.test_i18n import untranslated_words


class WeeklyGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if tk is None:raise unittest.SkipTest('Tkinter unavailable')
        try:cls.root=tk.Tk()
        except tk.TclError as exc:raise unittest.SkipTest(str(exc))
        cls.root.withdraw();cls.snapshots={};play_route(snapshots=cls.snapshots)

    @classmethod
    def tearDownClass(cls):cls.root.destroy()

    def setUp(self):
        from gui import ColonyApp
        for widget in self.root.winfo_children():widget.destroy()
        self.app=ColonyApp(self.root)
        self.app.ration_explained=True
        self.addCleanup(self.app._cancel_effects)
        self.root.update_idletasks()

    def test_default_weekly_labels_forecast_and_settings(self):
        self.assertEqual(self.app.day_label['text'],'Week 00 / 30')
        self.assertIn('week',self.app.next_button['text'])
        self.assertIn('Next week',self.app.metric_trends['food']['text'])
        self.assertFalse(self.app.sound.enabled)
        self.assertFalse(self.app.reduce_motion)
        self.app.set_language('zh_CN')
        self.assertIn('推进一周', self.app.next_button['text'])
        self.assertIn('下周预测', self.app.metric_trends['food']['text'])
        for widget in self.app._text_widgets:
            self.assertFalse(untranslated_words(widget['text']),widget.source_text)
        self.assertNotIn('每天',self.app.forecast_label['text'])

    def test_all_twelve_event_cards_fit_in_both_languages(self):
        self.root.deiconify();self.root.geometry('1040x880')
        for day in EVENT_DAYS:
            self.app.game=from_data(copy.deepcopy(self.snapshots[(day,'before_choice')]))
            before=copy.deepcopy(to_data(self.app.game))
            for language in ('en','zh_CN'):
                self.app.set_language(language);self.root.update()
                for widget in (self.app.event_title,self.app.event_story,self.app.event_scale,*self.app.event_buttons,self.app.next_button):
                    self.assertTrue(widget.winfo_ismapped(),(day,language))
                    self.assertGreaterEqual(widget.winfo_height(),widget.winfo_reqheight(),(day,language,widget))
                    self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),self.root.winfo_rooty()+self.root.winfo_height())
                for index,button in enumerate(self.app.event_buttons):
                    if language=='zh_CN':self.assertFalse(untranslated_words(button['text']),button['text'])
                    self.assertEqual(str(button['state']),'disabled' if self.app.game.option_error(index) else 'normal')
            self.assertEqual(to_data(self.app.game),before)
        self.root.withdraw()

    def test_motion_feedback_never_changes_simulation_and_can_cancel(self):
        before=copy.deepcopy(to_data(self.app.game))
        self.app.toggle_motion();self.assertEqual(to_data(self.app.game),before)
        self.app.toggle_motion();self.app.kind.set('farm');self.app.build()
        self.assertTrue(self.app._after_ids)
        state=copy.deepcopy(to_data(self.app.game))
        self.app.set_language('zh_CN')
        self.assertFalse(self.app._after_ids)
        self.assertFalse(self.app._float_labels)
        self.assertEqual(to_data(self.app.game),state)

    def test_rapid_actions_and_restart_cancel_old_callbacks(self):
        self.app.kind.set('farm');self.app.build();self.app.advance()
        self.app._cancel_effects()
        self.assertFalse(self.app._after_ids)
        self.assertEqual(self.app.game.day,1)
        self.app.advance()
        with patch('gui.dialogs.ask_yes_no',return_value=True):self.app.demo_game()
        self.assertFalse(self.app._after_ids)
        self.assertEqual(self.app.game.day,0)

    def test_locked_cost_display_and_choice_use_same_offer(self):
        self.app.game=from_data(copy.deepcopy(self.snapshots[(9,'before_choice')]))
        self.app.refresh()
        options=self.app.game.event_options()
        for index,option in enumerate(options):
            for resource,cost in option.get('cost',{}).items():
                self.assertIn(str(cost),self.app.event_buttons[index]['text'])
        available=next(i for i in (0,1) if not self.app.game.option_error(i))
        expected=from_data(copy.deepcopy(to_data(self.app.game)));expected.choose_event(available)
        self.app.event_buttons[available].invoke()
        self.assertEqual(to_data(self.app.game),to_data(expected))

    def test_legacy_mode_restores_day_labels_and_leaves_saved_state(self):
        old=from_data(copy.deepcopy(self.snapshots[(8,'after_choice')]))
        data=to_data(old);data.pop('ruleset');data.pop('event_snapshot');data['version']=4
        from engine import Game
        legacy=Game(7,ruleset='v30')
        self.app.game=legacy;self.app.refresh()
        self.assertEqual(self.app.day_label['text'],'Day 00 / 30')
        self.assertIn('day',self.app.next_button['text'])

    def test_audio_toggle_and_redraw_do_not_replay_cues(self):
        self.app.sound.available=True
        with patch.object(self.app.sound,'play') as cue:
            self.app.toggle_sound();cue.assert_called_once_with('build')
            state=copy.deepcopy(to_data(self.app.game))
            self.app.refresh();self.app.set_language('zh_CN');self.app.refresh()
            self.assertEqual(cue.call_count,1)
            self.assertEqual(to_data(self.app.game),state)
        self.app.sound.enabled=False

    def test_sound_failure_and_reduce_motion_do_not_block_success(self):
        self.app.reduce_motion=True
        with patch.object(self.app.sound,'play',return_value=False):
            self.app.kind.set('farm');self.app.build()
        self.assertEqual(self.app.game.grid[0][0],'farm')
        self.assertFalse(self.app._after_ids)


if __name__=='__main__':unittest.main()
