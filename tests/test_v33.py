"""Production-control invariants, factual chronicles and reachable compact UI."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from engine import Game, RuleError, EVENT_DAYS
from persistence import to_data, from_data, save_game, load_game, SaveError
from chronicle import entries, latest
from tests.test_v31 import play_route
from tests.test_i18n import untranslated_words


def small_colony():
    game=Game(7)
    game.build(0,0,'farm');game.next_day()
    game.build(0,1,'mine');game.next_day()
    game.choose_event(1)
    game.build(1,0,'home')
    return game


class ProductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshots={}
        cls.winner,cls.trace=play_route(ruleset='v33',snapshots=cls.snapshots)

    def test_no_switches_matches_old_trace_and_quotes_one_hundred_seeds(self):
        self.assertEqual(Game(7).ruleset,'v33')
        for seed in range(100):
            old,old_trace=play_route(seed,ruleset='v32')
            new,new_trace=play_route(seed,ruleset='v33')
            self.assertEqual(old_trace,new_trace,seed)
            self.assertEqual(old.result(),new.result())

    def test_pause_preserves_crew_and_resources_and_restores_forecast(self):
        game=small_colony();before=copy.deepcopy(to_data(game));forecast=game.forecast()
        game.toggle_facility(0,0)
        for key in ('food','energy','materials','happiness','population','built_today','day','ration_uses'):
            self.assertEqual(getattr(game,key),before[key],key)
        self.assertTrue(game.paused[0][0]);self.assertFalse(game.paused[1][0])
        self.assertEqual(game.facility_status(0,0),'PAUSED BY YOU')
        game.toggle_facility(0,0)
        self.assertEqual(game.forecast(),forecast)

    def test_food_reserve_can_release_power_for_mine_and_saves_no_extra_energy(self):
        game=small_colony();game.energy=4
        before=game.forecast()
        self.assertIn((0,1),before['offline_tiles'])
        game.toggle_facility(0,0);after=game.forecast()
        self.assertEqual(after['farms'],0);self.assertEqual(after['farm_bonus'],0)
        self.assertEqual(after['mines'],1)
        self.assertEqual(after['facility_power'],3)
        self.assertEqual(after['new_energy'],0)
        self.assertNotIn((0,0),after['offline_tiles'])
        self.assertEqual(after['paused_tiles'],[(0,0)])
        self.assertEqual(after['food'],-game.population)

    def test_stopping_mine_removes_only_its_noise_and_ore_requires_powered_mine(self):
        game=small_colony();game.grid[1][0]='home'
        # Add a second test-only neighbouring home to exercise the noise cap.
        game.grid[1][1]='home';game.levels[1][1]=1
        game.energy=30;game.effects['ore_rush']=2
        self.assertEqual(game.forecast()['ore_bonus'],8)
        self.assertEqual(game.pollution(),2)
        game.toggle_facility(0,1)
        self.assertEqual(game.pollution(),0)
        self.assertEqual(game.forecast()['ore_bonus'],0)
        game.toggle_facility(0,1);game.energy=0
        self.assertEqual(game.forecast()['ore_bonus'],0)

    def test_paused_upgrade_keeps_switch_and_cold_filter_effects_keep_ticking(self):
        game=small_colony();game.toggle_facility(0,0)
        game.next_day();game.effects={'cold_snap':2,'filter_load':3}
        game.materials=30;game.upgrade(0,0)
        self.assertTrue(game.paused[0][0]);self.assertEqual(game.levels[0][0],2)
        expected=game.forecast();before={key:getattr(game,key) for key in ('food','energy','materials')}
        game.next_day()
        for key,value in before.items():self.assertEqual(getattr(game,key)-value,expected[key])
        self.assertEqual(game.effects,{'cold_snap':1,'filter_load':2})
        self.assertTrue(game.paused[0][0])

    def test_invalid_actions_are_atomic_and_legacy_does_not_gain_controls(self):
        game=small_colony()
        for coords in ((2,2),(4,4),(-1,0),(True,0),(0,5)):
            before=copy.deepcopy(to_data(game))
            with self.assertRaises(RuleError):game.toggle_facility(*coords)
            self.assertEqual(to_data(game),before)
        game.next_day();game.next_day();game.next_day()
        self.assertTrue(game.pending_event)
        before=copy.deepcopy(to_data(game))
        with self.assertRaises(RuleError):game.toggle_facility(0,0)
        self.assertEqual(to_data(game),before)
        for mode in ('v20','v30','v31','v32'):
            old=Game(7,campaign_days=15 if mode=='v20' else 30,ruleset=mode)
            old.build(0,0,'farm')
            with self.assertRaises(RuleError):old.toggle_facility(0,0)
        with self.assertRaises(RuleError):self.winner.toggle_facility(0,0)

    def test_choice_and_ration_preview_share_paused_settlement_without_mutation(self):
        for day in EVENT_DAYS:
            game=from_data(copy.deepcopy(self.snapshots[(day,'before_choice')]))
            game.paused[0][0]=True
            before=copy.deepcopy(to_data(game))
            for index in (0,1):
                if game.option_error(index):continue
                preview=game.preview_choice(index);candidate=from_data(before);candidate.choose_event(index)
                if candidate.status=='active':self.assertEqual(preview,{'ended':False,**candidate.forecast()})
            self.assertEqual(to_data(game),before)
        game=small_colony();game.toggle_facility(0,0)
        before=copy.deepcopy(to_data(game));preview=game.ration_preview()
        game.emergency_rations();self.assertEqual(game.forecast()['deaths'],preview['deaths_after'])
        self.assertNotEqual(to_data(game),before)

    def test_disk_roundtrip_and_schema6_migration_preserve_rules(self):
        game=small_colony();game.toggle_facility(0,0)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'switch.json';save_game(game,path)
            restored=load_game(path)
            self.assertEqual(to_data(restored),to_data(game));self.assertEqual(restored.forecast(),game.forecast())
        old=Game(7,ruleset='v32');data=to_data(old);data.pop('paused');data['version']=6
        restored=from_data(data)
        self.assertEqual(restored.ruleset,'v32');self.assertFalse(any(map(any,restored.paused)))
        self.assertEqual(restored.forecast(),old.forecast())

    def test_invalid_switch_data_and_downgrade_cannot_change_live_game(self):
        base=to_data(small_colony())
        for switches in ([],[[False]*5]*4,[[False]*4]*5,'no',None):
            bad=copy.deepcopy(base);bad['paused']=switches
            with self.assertRaises(SaveError):from_data(bad)
        for row,column,value in ((0,0,1),(2,2,True),(4,4,True)):
            bad=copy.deepcopy(base);bad['paused'][row][column]=value
            with self.assertRaises(SaveError):from_data(bad)
        bad=copy.deepcopy(base);bad['ruleset']='v32';bad['paused'][0][0]=True
        with self.assertRaises(SaveError):from_data(bad)
        bad=copy.deepcopy(base);bad['version']=6;bad.pop('paused')
        with self.assertRaises(SaveError):from_data(bad)
        candidate=from_data(base);base['paused'][0][0]=True
        self.assertFalse(candidate.paused[0][0])

    def test_chronicle_retains_stories_ignores_routine_and_is_read_only(self):
        game=small_colony();before=copy.deepcopy(to_data(game))
        initial=entries(game);self.assertTrue(any('window lights' in text for _,text in initial))
        game._record('Production A1: PAUSED.');game._record('Next growth check: Week 4.')
        self.assertEqual(entries(game),initial)
        expected=latest(game);data=copy.deepcopy(to_data(game))
        self.assertEqual(latest(from_data(data)),expected)
        entries(game);latest(game);self.assertEqual(to_data(game),data)
        self.assertTrue(before['log'])

    def test_legal_power_example_settles_as_preview_and_timers_expire(self):
        game=load_game(Path(__file__).resolve().parents[1]/'examples/power_management_before.json')
        self.assertEqual((game.food,game.energy,game.materials,game.population),(93,1,15,12))
        self.assertEqual(game.forecast()['offline'],1)
        game.toggle_facility(0,0);forecast=game.forecast()
        self.assertEqual((forecast['food'],forecast['materials'],forecast['offline']),(-1,9,0))
        before={key:getattr(game,key) for key in ('food','energy','materials','population','happiness')}
        game.next_day()
        for key,value in before.items():self.assertEqual(getattr(game,key)-value,forecast[key])
        self.assertNotIn('dust_cloud',game.effects)
        self.assertTrue(game.paused[0][0])
        restored=from_data(to_data(game));restored.toggle_facility(0,0)
        self.assertFalse(restored.paused[0][0])

    def test_multiple_mine_switches_respect_noise_cap(self):
        game=Game(7)
        for r,c,kind in ((0,0,'mine'),(0,1,'home'),(4,4,'mine'),(4,3,'home')):
            game.grid[r][c]=kind;game.levels[r][c]=1
        self.assertEqual(game.pollution(),4)
        game.toggle_facility(0,0);self.assertEqual(game.pollution(),2)
        game.toggle_facility(4,4);self.assertEqual(game.pollution(),0)
        game.toggle_facility(0,0);self.assertEqual(game.pollution(),2)

    def test_chronicle_does_not_invent_dates_for_truncated_old_log(self):
        from narrative import REACTIONS
        game=Game(7);game.log=[REACTIONS['storm'][0][0]]
        self.assertEqual(latest(game),(None,game.log[0]))


class CompactGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        try:cls.root=tk.Tk()
        except tk.TclError as exc:raise unittest.SkipTest(str(exc))
        cls.root.withdraw();cls.snapshots={};play_route(ruleset='v33',snapshots=cls.snapshots)

    @classmethod
    def tearDownClass(cls):cls.root.destroy()

    def setUp(self):
        import dialogs
        from gui import ColonyApp
        dialogs.close_readers(self.root)
        for widget in self.root.winfo_children():widget.destroy()
        self.app=ColonyApp(self.root)
        self.addCleanup(self.app._cancel_effects)
        self.addCleanup(lambda:dialogs.close_readers(self.root))

    def test_map_share_and_controls_at_wide_and_compact_sizes(self):
        self.root.deiconify()
        for geometry in ('1320x860','1280x720','980x680'):
            self.root.geometry(geometry)
            for language in ('en','zh_CN'):
                self.app.set_language(language);self.root.update()
                self.assertGreater(self.app.board.winfo_width(),self.app.details_frame.winfo_width()*1.25)
                self.assertGreaterEqual(self.app.board.winfo_height(),180)
                for widget in (self.app.next_button,self.app.chronicle_text,self.app.beacon_button,self.app.ration_button):
                    self.assertTrue(widget.winfo_ismapped())
                    self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),self.root.winfo_rooty()+self.root.winfo_height())
                if language=='zh_CN':
                    self.assertFalse(untranslated_words(self.app.chronicle_title['text']))
                    self.assertFalse(untranslated_words(self.app.production_hint['text']))
        self.root.withdraw()

    def test_all_councils_scroll_to_choices_in_compact_both_languages(self):
        self.root.deiconify();self.root.geometry('1280x720')
        for day in EVENT_DAYS:
            self.app.game=from_data(copy.deepcopy(self.snapshots[(day,'before_choice')]))
            before=copy.deepcopy(to_data(self.app.game))
            for language in ('en','zh_CN'):
                self.app.set_language(language);self.root.update();self.app.detail_canvas.yview_moveto(1);self.root.update()
                for widget in self.app.event_buttons:
                    self.assertTrue(widget.winfo_ismapped())
                    self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),
                        self.app.detail_canvas.winfo_rooty()+self.app.detail_canvas.winfo_height()+2)
                    self.assertGreaterEqual(widget.winfo_rooty(),self.app.detail_canvas.winfo_rooty()-2)
                    if language=='zh_CN':self.assertFalse(untranslated_words(widget['text']),widget['text'])
            self.assertEqual(to_data(self.app.game),before)
        self.root.withdraw()

    def test_toggle_and_forecast_labels_match_actual_state_in_both_languages(self):
        self.app.game=small_colony();self.app.selected=(0,0);self.app.refresh()
        for language in ('en','zh_CN'):
            self.app.set_language(language)
            self.app.pause_button.invoke();self.assertTrue(self.app.game.paused[0][0])
            self.assertEqual(self.app.metrics['energy']['text'],self.app.tr(f'Energy  {self.app.game.energy}'))
            forecast=self.app.game.forecast()
            self.assertEqual(self.app.metric_trends['energy']['text'],self.app.tr(f"Next week {forecast['energy']:+d}"))
            self.assertIn(self.app.tr('PAUSED BY YOU'),self.app.production_hint['text'])
            self.assertFalse(untranslated_words(self.app.production_hint['text']) if language=='zh_CN' else [])
            self.app.pause_button.invoke();self.assertFalse(self.app.game.paused[0][0])

    def test_history_reader_contains_multiple_records_and_reading_changes_nothing(self):
        import dialogs
        self.app.game=small_colony();self.app.refresh();before=copy.deepcopy(to_data(self.app.game))
        self.root.deiconify();self.app.history_button.invoke();self.root.update()
        reader=next(w for w in self.root.winfo_children() if isinstance(w,dialogs.GameWindow))
        self.assertIn('window lights up',reader.body.get('1.0','end'))
        self.assertEqual(to_data(self.app.game),before)
        reader.close();self.root.withdraw()


if __name__=='__main__':unittest.main()
