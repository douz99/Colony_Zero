"""Player-facing clarity, truthful memories and small late-choice revisions."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from engine import Game, EVENT_DAYS
from events import offer_options
from persistence import from_data,to_data,SaveError,load_game
from tests.test_v31 import play_route
from tests.test_i18n import untranslated_words
from i18n import translate


class V32RulesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshots={}
        cls.winner,cls.trace=play_route(ruleset='v32',snapshots=cls.snapshots)

    def test_default_version_and_first_eight_turns_match(self):
        self.assertEqual(Game(7,ruleset='v32').ruleset,'v32')
        for seed in range(100):
            _,old=play_route(seed,ruleset='v31')
            _,new=play_route(seed,ruleset='v32')
            self.assertEqual([row[:7] for row in old[:8]],[row[:7] for row in new[:8]],seed)

    def test_revised_choices_only_after_opening(self):
        for event in ('immigrants','fault','community'):
            self.assertEqual(offer_options(event,5,5,'v31'),offer_options(event,5,5,'v32'))
        self.assertEqual(offer_options('immigrants',14,7,'v32')[0]['cost']['food'],11)
        self.assertEqual(offer_options('immigrants',14,7,'v32')[0]['change']['materials'],6)
        self.assertEqual(offer_options('fault',18,10,'v32')[0]['cost']['materials'],15)
        self.assertEqual(offer_options('fault',18,10,'v32')[0]['change']['energy'],4)
        self.assertEqual(offer_options('community',28,13,'v32')[0]['cost'],{'food':41,'energy':20})
        self.assertEqual(offer_options('community',28,13,'v32')[0]['change']['happiness'],12)

    def test_reference_win_and_conservative_rating(self):
        self.assertEqual(self.winner.result(),('New Eden',394))
        self.assertEqual((self.winner.food,self.winner.energy,self.winner.materials,self.winner.population,self.winner.happiness),(66,55,72,13,88))
        cautious,_=play_route(ruleset='v32',policy='second')
        self.assertEqual((cautious.status,cautious.result()[0]),('won','Struggling Outpost'))
        old,_=play_route(ruleset='v31',policy='second')
        self.assertEqual(old.result()[0],'Prosperous Colony')

    def test_two_openings_and_recovery_can_still_win(self):
        for opening,rescue in (('farm',False),('solar',False),('farm',True)):
            game,_=play_route(ruleset='v32',opening=opening,rescue=rescue)
            self.assertEqual(game.status,'won',(opening,rescue))

    def test_choice_previews_match_real_choices_without_side_effects(self):
        for day in EVENT_DAYS:
            game=from_data(copy.deepcopy(self.snapshots[(day,'before_choice')]))
            before=copy.deepcopy(to_data(game))
            for index in (0,1):
                preview=game.preview_choice(index)
                self.assertEqual(to_data(game),before)
                if game.option_error(index):
                    self.assertIn('error',preview)
                else:
                    actual=from_data(copy.deepcopy(before));actual.choose_event(index)
                    if actual.status=='active':
                        for key in ('food','energy','materials','population','happiness','deaths'):
                            self.assertEqual(preview[key],actual.forecast()[key])

    def test_ration_preview_is_truthful_and_does_not_spend(self):
        game=Game(7);game.food=2
        before=copy.deepcopy(to_data(game));preview=game.ration_preview()
        self.assertEqual((preview['meals_before'],preview['meals_after'],preview['deaths_before'],preview['deaths_after']),(4,2,1,0))
        self.assertEqual(to_data(game),before)
        game.emergency_rations();game.next_day()
        self.assertEqual(game.memories['ration_rescues'],1)
        self.assertEqual(game.population,4)

    def test_unnecessary_rations_do_not_claim_rescues(self):
        game=Game(7);game.emergency_rations();game.next_day()
        self.assertEqual(game.memories['ration_rescues'],0)

    def test_objective_opportunities_and_known_states(self):
        game=Game(7)
        self.assertEqual(game.objective_status()['state'],'locked')
        game.day=6;self.assertEqual(game.objective_status()['state'],'ready')
        game.built_today=True;self.assertEqual(game.objective_status()['state'],'crew')
        game.day=28;game.beacon_stage=1
        self.assertEqual(game.objective_status()['state'],'impossible')
        game.built_today=False;self.assertEqual(game.objective_status()['opportunities'],2)
        self.assertNotEqual(game.objective_status()['state'],'impossible')

    def test_six_bulletins_are_saved_and_not_replayed_on_read(self):
        self.assertEqual(len(self.winner.bulletins_seen),6)
        for data in self.snapshots.values():
            game=from_data(data)
            self.assertEqual(to_data(from_data(to_data(game))),data)

    def test_story_variants_are_stable_and_do_not_change_deck(self):
        titles=set()
        for seed in range(8):
            snapshots={};play_route(seed,ruleset='v32',snapshots=snapshots)
            for data in snapshots.values():
                if not data['pending_event']:continue
                game=from_data(data);before=copy.deepcopy(to_data(game))
                title=game.event_view()['title'];titles.add(title)
                self.assertEqual(game.event_view(),from_data(before).event_view())
                self.assertEqual(to_data(game),before)
        self.assertIn('Five Small Lights',titles)
        self.assertIn('The Evening We Kept',titles)

    def test_memories_reflect_actual_actions(self):
        self.assertEqual(self.winner.memories,{'home_week':4,'beacon_week':23,'welcomed':2,'ration_rescues':0})
        self.assertIn('Week 23',self.winner.memory_summary())

    def test_legacy_v5_keeps_old_rating_and_has_no_fabricated_history(self):
        old,_=play_route(ruleset='v31',policy='second')
        data=to_data(old)
        for key in ('story_seed','memories','bulletins_seen','paused'):data.pop(key)
        data['version']=5
        restored=from_data(data)
        self.assertEqual((restored.ruleset,restored.result()),('v31',old.result()))
        self.assertEqual(restored.memories,{'home_week':None,'beacon_week':None,'welcomed':0,'ration_rescues':0})

    def test_invalid_memories_and_story_fields_rejected(self):
        for key,value in (('story_seed',True),('story_seed',-1),('bulletins_seen',['week27']),('memories',{})):
            data=to_data(Game(7));data[key]=value
            with self.assertRaises(SaveError):from_data(data)
        for key,value in (('home_week',0),('beacon_week',22),('welcomed',2),('ration_rescues',1)):
            data=to_data(Game(7));data['memories'][key]=value
            with self.assertRaises(SaveError):from_data(data)

    def test_new_prose_and_goal_explanations_translate(self):
        for data in self.snapshots.values():
            game=from_data(data)
            texts=[*game.log,game.memory_summary(),game.objective_status()['text'],game.ration_help()]
            if game.pending_event:texts += [game.event_view()['story'],game.event_view()['title']]
            for text in texts:
                self.assertFalse(untranslated_words(translate(text,'zh_CN')),text)


try:
    import tkinter as tk
except ImportError:
    tk=None


class V32GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if tk is None:raise unittest.SkipTest('Tkinter unavailable')
        try:cls.root=tk.Tk()
        except tk.TclError as exc:raise unittest.SkipTest(str(exc))
        cls.root.withdraw();cls.snapshots={};play_route(ruleset='v32',snapshots=cls.snapshots)

    @classmethod
    def tearDownClass(cls):cls.root.destroy()

    def setUp(self):
        from gui import ColonyApp
        import dialogs
        dialogs.close_readers(self.root)
        for widget in self.root.winfo_children():widget.destroy()
        self.app=ColonyApp(self.root)
        self.addCleanup(self.app._cancel_effects)
        self.addCleanup(lambda:dialogs.close_readers(self.root))
        self.root.update_idletasks()

    def test_first_ration_cancel_does_not_spend_then_confirmation_applies(self):
        self.app.game.food=2
        before=copy.deepcopy(to_data(self.app.game))
        with patch('gui.dialogs.ask_yes_no',return_value=False) as confirm:
            self.app.ration_button.invoke()
            self.assertIn('Meals 4 -> 2',confirm.call_args.args[1])
            self.assertIn('Expected losses 1 -> 0',confirm.call_args.args[1])
        self.assertEqual(to_data(self.app.game),before)
        with patch('gui.dialogs.ask_yes_no',return_value=True):self.app.ration_button.invoke()
        self.assertEqual((self.app.game.ration_uses,self.app.game.happiness),(1,62))
        self.assertIn('ACTIVE',self.app.ration_button['text'])

    def test_keyboard_ration_explanation_has_no_side_effect(self):
        before=copy.deepcopy(to_data(self.app.game))
        self.assertIn('Happiness -8',self.app.ration_tip.text())
        self.root.deiconify();self.root.update()
        self.app.ration_tip.show();self.root.update()
        self.assertTrue(self.app.ration_tip.window.winfo_exists())
        self.app.ration_tip.dismiss()
        self.assertEqual(to_data(self.app.game),before)
        self.root.withdraw()

    def test_final_week_warning_cancel_and_continue(self):
        snapshots={};play_route(ruleset='v32',objective=False,snapshots=snapshots)
        self.app.game=from_data(snapshots[(29,'after_choice')]);self.app.refresh()
        before=copy.deepcopy(to_data(self.app.game))
        with patch('gui.dialogs.ask_yes_no',return_value=False):self.app.advance()
        self.assertEqual(to_data(self.app.game),before)
        with patch('gui.dialogs.ask_yes_no',return_value=True):self.app.advance()
        self.assertEqual(self.app.game.result()[0],'Stranded Colony')

    def test_report_and_guide_are_scrollable_reused_readers(self):
        import dialogs
        before=copy.deepcopy(to_data(self.app.game))
        self.root.deiconify();self.app.show_guide();self.root.update()
        windows=[w for w in self.root.winfo_children() if isinstance(w,dialogs.GameWindow)]
        self.assertEqual(len(windows),1)
        reader=windows[0]
        self.assertIn('beacon',reader.body.get('1.0','end'))
        self.app.show_guide();self.root.update()
        self.assertEqual(len([w for w in self.root.winfo_children() if isinstance(w,dialogs.GameWindow)]),1)
        reader.set_message('\n'.join(f'Line {i}' for i in range(200)));self.root.update()
        self.assertLess(reader.body.yview()[1],1)
        reader.close();self.app.show_report();self.root.update()
        self.assertEqual(to_data(self.app.game),before)
        self.root.withdraw()

    def test_real_confirmation_buttons_and_escape_result(self):
        import dialogs
        self.root.deiconify();self.root.update()
        def choose():
            window=next(w for w in self.root.winfo_children() if isinstance(w,dialogs.GameWindow))
            window.confirm_button.invoke()
        self.root.after(80,choose)
        self.assertTrue(dialogs.ask_yes_no('Confirm','A test choice',parent=self.root))
        def cancel():
            window=next(w for w in self.root.winfo_children() if isinstance(w,dialogs.GameWindow))
            window.close_button.invoke()
        self.root.after(80,cancel)
        self.assertFalse(dialogs.ask_yes_no('Confirm','A test choice',parent=self.root))
        self.root.withdraw()

    def test_new_event_previews_fit_both_languages(self):
        self.root.deiconify();self.root.geometry('1040x880')
        for day in EVENT_DAYS:
            self.app.game=from_data(copy.deepcopy(self.snapshots[(day,'before_choice')]))
            before=copy.deepcopy(to_data(self.app.game))
            for language in ('en','zh_CN'):
                self.app.set_language(language);self.root.update()
                for widget in (*self.app.event_buttons,self.app.event_story,self.app.next_button):
                    self.assertTrue(widget.winfo_ismapped())
                    self.assertGreaterEqual(widget.winfo_height(),widget.winfo_reqheight(),(day,language,widget))
                    self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),self.root.winfo_rooty()+self.root.winfo_height())
                if language=='zh_CN':
                    for widget in (self.app.mission_label,self.app.event_story,*self.app.event_buttons):
                        self.assertFalse(untranslated_words(widget['text']),widget['text'])
            self.assertEqual(to_data(self.app.game),before)
        self.root.withdraw()

    def test_common_invalid_action_is_not_a_system_messagebox(self):
        self.app.game.materials=0
        with patch('gui.dialogs.show_info') as information:
            self.app.build();information.assert_not_called()
        self.assertIn('Need 10 Materials',self.app.feedback_label['text'])
        import gui
        self.assertFalse(hasattr(gui,'messagebox'))

    def test_action_cues_cover_ration_choice_and_settlement_without_redraw_replay(self):
        self.app.ration_explained=True
        with patch.object(self.app.sound,'play') as cue:
            self.app.use_rations();cue.assert_called_with('ration')
            self.app.advance();cue.assert_called_with('settle')
            count=cue.call_count;self.app.refresh();self.app.set_language('zh_CN')
            self.assertEqual(cue.call_count,count)


if __name__=='__main__':unittest.main()
