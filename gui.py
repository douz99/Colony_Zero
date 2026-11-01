"""A compact Tkinter interface; resource rules live entirely in engine.py."""

import tkinter as tk
from tkinter import filedialog, ttk
import dialogs
from tkinter import font as tkfont
from pathlib import Path

from engine import BUILDINGS, Game, LAST_DAY, RuleError, SIZE, UPGRADE_COSTS, facility_effect
from events import EVENTS, describe_option
from persistence import SaveError, load_game, save_game
from visuals import draw_board
from i18n import LANGUAGES, translate, weekly_chinese
from localized_widgets import LocalizedButton, LocalizedLabel, LocalizedRadio
from soundfx import SoundPlayer

BG = "#0b1624"
PANEL = "#182b3e"
TEXT = "#e8eff6"
MUTED = "#b7c9dc"
ACCENT = "#73d9cf"


class ColonyApp:
    """Render a Game and translate button presses into validated actions."""

    def __init__(self, root):
        self.root = root
        self.language = "en"
        available_fonts = set(tkfont.families(root))
        self.chinese_font = next((name for name in ("Microsoft YaHei UI", "Microsoft YaHei", "Noto Sans CJK SC")
                                  if name in available_fonts), "Segoe UI")
        self.language_choice = tk.StringVar(root, value="English")
        self._text_widgets = []
        self.game = Game()
        self.sound = SoundPlayer()
        self.reduce_motion = False
        self._after_ids = set()
        self._float_labels = []
        self._render_ruleset = None
        self.ration_explained = False
        self.selected = (0, 0)
        self.kind = tk.StringVar(root, value="solar")
        self.feedback = "Welcome, Governor. Build food production before the supplies run out."
        root.title("Colony Zero | V3.3")
        root.update_idletasks()
        width=min(1320,max(900,root.winfo_screenwidth()-70))
        height=min(860,max(620,root.winfo_screenheight()-130))
        root.geometry(f'{width}x{height}')
        root.minsize(980,680)
        root.configure(bg=BG)
        root.option_add("*Font", ("Segoe UI", 10))
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._create_widgets()
        root.bind("<Configure>", self._fit_header)
        self.refresh()

    def tr(self, text):
        localized = translate(text, self.language)
        if self.game.ruleset in ("v31", "v32", "v33"):
            if self.language == "en":
                if "\\" in localized or ".json" in localized:
                    return localized
                return self.game.time_text(localized)
            return weekly_chinese(localized)
        return localized

    def set_language(self, language):
        """Change presentation only; never replace or update the Game object."""
        if language not in LANGUAGES.values():
            raise ValueError("Unsupported interface language.")
        self._cancel_effects()
        dialogs.close_readers(self.root)
        self.language = language
        self.language_choice.set(next(label for label, code in LANGUAGES.items() if code == language))
        for widget in self._text_widgets:
            widget.retranslate()
            widget.set_font_family(self.chinese_font if language == "zh_CN" else None)
        self.language_selector.configure(font=(self.chinese_font if language == "zh_CN" else "Segoe UI", 10))
        self.refresh()

    def _schedule(self, delay, callback):
        def run():
            self._after_ids.discard(job)
            callback()
        job = self.root.after(delay, run)
        self._after_ids.add(job)

    def _cancel_effects(self):
        if hasattr(self, 'ration_tip'):
            self.ration_tip.dismiss()
            self.goal_tip.dismiss()
            self.sound_tip.dismiss()
        for job in self._after_ids:
            self.root.after_cancel(job)
        self._after_ids.clear()
        for label in self._float_labels:
            label.destroy()
        self._float_labels.clear()
        if hasattr(self, 'mission_frame'):
            self.mission_frame.configure(bg=PANEL)
        if hasattr(self, 'board'):
            self.board.delete('action_flash')

    def toggle_motion(self):
        self.reduce_motion = not self.reduce_motion
        self._cancel_effects()
        self.refresh()

    def toggle_sound(self):
        if self.sound.enabled:
            self.sound.stop()
            self.sound.enabled = False
        elif self.sound.available:
            self.sound.enabled = True
            self.sound.play('build')
        self.refresh()

    def _register(self, widget):
        self._text_widgets.append(widget)
        return widget

    def _info(self, title, message, **options):
        return dialogs.show_info(self.tr(title), self.tr(message), close_label=self.tr('Close'),
                                 font_family=self.chinese_font if self.language == 'zh_CN' else 'Segoe UI', **options)

    def _error(self, title, message, **options):
        return self._info(title, message, **options)

    def _ask(self, title, message, **options):
        options.setdefault('confirm_label', self.tr('Confirm'))
        options.setdefault('cancel_label', self.tr('Back'))
        return dialogs.ask_yes_no(self.tr(title), self.tr(message),
                                 font_family=self.chinese_font if self.language == 'zh_CN' else 'Segoe UI', **options)

    def _fit_header(self, event):
        if event.widget == self.root:
            width = max(400, event.width - 40)
            self.forecast_label.configure(wraplength=width)
            self.feedback_label.configure(wraplength=width)
            self.mission_label.configure(wraplength=max(210,width-480))
            self.chronicle_text.configure(wraplength=max(300,width-170))
            self.chronicle_text.configure(height=1 if event.height < 760 else 2)
            if event.width < 1100:
                self.chronicle_title.pack_forget()
            elif not self.chronicle_title.winfo_manager():
                self.chronicle_title.pack(before=self.chronicle_text,fill='x')
            self.site_hint.configure(wraplength=max(280,int(width*.6)-45))

    def label(self, parent, text="", **kwargs):
        kwargs.setdefault("bg", PANEL)
        kwargs.setdefault("fg", TEXT)
        return self._register(LocalizedLabel(parent, self.tr, text=text, **kwargs))

    def button(self, parent, text, command, **kwargs):
        kwargs.setdefault("bg", "#2b4761")
        kwargs.setdefault("fg", TEXT)
        kwargs.setdefault("padx", 10)
        kwargs.setdefault("pady", 6)
        return self._register(LocalizedButton(parent, self.tr, text=text, command=command, relief="flat",
                         activebackground="#416782", activeforeground="white",
                         disabledforeground="#8796a3", cursor="hand2", **kwargs))

    def _create_widgets(self):
        top=tk.Frame(self.root,bg=BG)
        top.pack(fill='x',padx=16,pady=(8,4))
        self.label(top,'COLONY ZERO',bg=BG,fg=ACCENT,font=('Segoe UI',19,'bold')).pack(side='left')
        for title,callback in (('New',self.new_game),('Demo (seed 7)',self.demo_game),
                ('Save',self.save),('Load',self.load),('Report',self.show_report),('Guide',self.show_guide)):
            self.button(top,title,callback,padx=8,pady=4).pack(side='left',padx=(7,0))
        self.day_label=self.label(top,bg=BG,font=('Segoe UI',12,'bold'))
        self.day_label.pack(side='right')
        toolbar=tk.Frame(self.root,bg=BG)
        toolbar.pack(fill='x',padx=18,pady=(0,4))
        self.label(toolbar,'FOUR PIONEERS. ONE PLACE TO CALL HOME.',bg=BG,fg=MUTED,font=('Segoe UI',9)).pack(side='left')
        self.language_selector=ttk.Combobox(toolbar,textvariable=self.language_choice,
            values=tuple(LANGUAGES),state='readonly',width=11,font=('Segoe UI',10))
        self.language_selector.pack(side='right')
        self.language_selector.bind('<<ComboboxSelected>>',lambda e:self.set_language(LANGUAGES[self.language_choice.get()]))
        self.sound_button=self.button(toolbar,'Sound: off',self.toggle_sound,pady=2,padx=6,font=('Segoe UI',9))
        self.sound_button.pack(side='right',padx=6)
        self.motion_button=self.button(toolbar,'Motion: on',self.toggle_motion,pady=2,padx=6,font=('Segoe UI',9))
        self.motion_button.pack(side='right')
        metrics=tk.Frame(self.root,bg=BG);self.metrics_frame=metrics
        metrics.pack(fill='x',padx=16,pady=(0,5))
        self.metrics={};self.metric_trends={}
        for index,name in enumerate(('food','energy','materials','population')):
            metrics.columnconfigure(index,weight=1,uniform='stocks')
            label=self.label(metrics,font=('Segoe UI',14,'bold'),padx=8,pady=3)
            label.grid(row=0,column=index,sticky='ew',padx=(0,5));self.metrics[name]=label
            trend=self.label(metrics,font=('Segoe UI',9),padx=8,fg=MUTED)
            trend.grid(row=1,column=index,sticky='ew',padx=(0,5));self.metric_trends[name]=trend
        morale=tk.Frame(self.root,bg=BG);morale.pack(fill='x',padx=18,pady=(0,4))
        self.happiness_label=self.label(morale,bg=BG,fg=ACCENT);self.happiness_label.pack(side='left')
        self.happiness_bar=tk.Canvas(morale,bg=PANEL,width=150,height=10,highlightthickness=0)
        self.happiness_bar.pack(side='left',padx=10)
        self.label(morale,'Growth needs 40+  |  New Eden needs 80+',bg=BG,fg=MUTED,font=('Segoe UI',9)).pack(side='left')
        self.crew_icons=tk.Canvas(morale,bg=BG,width=160,height=20,highlightthickness=0);self.crew_icons.pack(side='right')
        mission=tk.Frame(self.root,bg=PANEL,padx=8,pady=4);self.mission_frame=mission
        mission.pack(fill='x',padx=16,pady=(0,5))
        self.beacon_progress=tk.Canvas(mission,width=65,height=24,bg=PANEL,highlightthickness=0)
        self.beacon_progress.pack(side='left',padx=(0,7))
        self.beacon_button=self.button(mission,'Work on HQ beacon',lambda:self._action(self.game.repair_beacon),pady=3,padx=7)
        self.beacon_button.pack(side='right')
        self.ration_button=self.button(mission,'Emergency rations (2 left)',self.use_rations,pady=3,padx=7)
        self.ration_button.pack(side='right',padx=7)
        self.mission_label=self.label(mission,anchor='w',justify='left',wraplength=600,font=('Segoe UI',9,'bold'))
        self.mission_label.pack(side='left',fill='x',expand=True)
        self.ration_tip=dialogs.HelpTip(self.ration_button,lambda:self.tr(self.game.ration_help()))
        self.goal_tip=dialogs.HelpTip(self.mission_label,lambda:self.tr(self.game.objective_status()['text']))
        self.sound_tip=dialogs.HelpTip(self.sound_button,lambda:self.tr('Sound starts off. Switch it on for short action cues.'))
        self.crew_label=self.label(self.root,bg=BG,fg=MUTED,anchor='w',font=('Segoe UI',9))
        # The full crew observation is shown in its tip; no separate header row.
        self.chronicle_frame=tk.Frame(self.root,bg='#203c49',padx=10,pady=6)
        self.chronicle_frame.pack(fill='x',padx=16,pady=(0,5))
        self.history_button=self.button(self.chronicle_frame,'Read history',self.show_history,pady=3)
        self.history_button.pack(side='right',padx=(8,0))
        self.chronicle_title=self.label(self.chronicle_frame,bg='#203c49',fg=ACCENT,anchor='w',font=('Segoe UI',9,'bold'))
        self.chronicle_title.pack(fill='x')
        self.chronicle_text=self.label(self.chronicle_frame,bg='#203c49',anchor='w',justify='left',height=2,wraplength=1000,font=('Segoe UI',10))
        self.chronicle_text.pack(fill='x')
        self.forecast_label=self.label(self.root,bg=BG,fg=ACCENT,anchor='w',justify='left',font=('Segoe UI',9))
        self.forecast_label.pack(fill='x',padx=18,pady=(0,3))
        self.feedback_label=self.label(self.root,bg=BG,fg='#e6b655',anchor='w',font=('Segoe UI',9,'bold'))
        self.feedback_label.pack(fill='x',padx=18,pady=(0,4))
        body=tk.Frame(self.root,bg=BG);self.body_frame=body
        body.pack(fill='both',expand=True,padx=16,pady=(0,10))
        body.columnconfigure(0,weight=3,uniform='work');body.columnconfigure(1,weight=2,uniform='work')
        body.rowconfigure(0,weight=1)
        left=tk.Frame(body,bg=PANEL,padx=9,pady=7);self.map_frame=left
        left.grid(row=0,column=0,sticky='nsew',padx=(0,9))
        self.label(left,'THE LANDING SITE',font=('Segoe UI',11,'bold'),anchor='w').pack(fill='x')
        self.board=tk.Canvas(left,bg=PANEL,highlightthickness=0,width=600,height=330,takefocus=True,cursor='hand2')
        self.board.pack(fill='both',expand=True,pady=4)
        self.board.bind('<Configure>',lambda e:self._draw_board());self.board.bind('<Button-1>',self._click_map)
        for key,dr,dc in (('Up',-1,0),('Down',1,0),('Left',0,-1),('Right',0,1)):
            self.board.bind(f'<{key}>',lambda e,r=dr,c=dc:self._move_selection(r,c))
        footer=tk.Frame(left,bg=PANEL);footer.pack(before=self.board,side='bottom',fill='x')
        self.site_hint=self.label(footer,anchor='w',justify='left',fg=ACCENT,wraplength=650,font=('Segoe UI',9))
        self.site_hint.pack(fill='x',pady=(2,3))
        self.next_button=self.button(footer,'Advance one day  >',self.advance,bg='#247d76',font=('Segoe UI',12,'bold'),pady=7)
        self.next_button.pack(fill='x')
        detail=tk.Frame(body,bg=PANEL);detail.grid(row=0,column=1,sticky='nsew')
        scroll=tk.Scrollbar(detail);scroll.pack(side='right',fill='y')
        self.detail_canvas=tk.Canvas(detail,bg=PANEL,highlightthickness=0,width=420,height=300,yscrollcommand=scroll.set)
        self.detail_canvas.pack(side='left',fill='both',expand=True);scroll.configure(command=self.detail_canvas.yview)
        right=tk.Frame(self.detail_canvas,bg=PANEL,padx=10,pady=7);self.details_frame=right
        item=self.detail_canvas.create_window((0,0),window=right,anchor='nw')
        self.detail_canvas.bind('<Configure>',lambda e:self.detail_canvas.itemconfigure(item,width=e.width))
        right.bind('<Configure>',self._fit_right_panel)
        self.construction_panel=tk.Frame(right,bg=PANEL);self.construction_panel.pack(fill='x')
        self.selection_label=self.label(self.construction_panel,anchor='w',justify='left',wraplength=440,font=('Segoe UI',10,'bold'))
        self.selection_label.pack(fill='x',pady=(0,4))
        choices=tk.Frame(self.construction_panel,bg=PANEL);choices.pack(fill='x')
        for index,(key,info) in enumerate(BUILDINGS.items()):
            choices.columnconfigure(index%2,weight=1,uniform='builds')
            radio=self._register(LocalizedRadio(choices,self.tr,text=f"{info['name']}   |   {info['cost']} Materials",
                variable=self.kind,value=key,command=self.refresh,anchor='w',justify='left',wraplength=190,
                bg=PANEL,fg=info['color'],selectcolor=BG,activebackground=PANEL,activeforeground=TEXT,
                padx=1,pady=2,font=('Segoe UI',9),cursor='hand2'))
            radio.grid(row=index//2,column=index%2,sticky='ew')
        actions=tk.Frame(self.construction_panel,bg=PANEL);actions.pack(fill='x',pady=5)
        self.build_button=self.button(actions,'Build selected facility',self.build,padx=5)
        self.build_button.pack(side='left',fill='x',expand=True,padx=(0,4))
        self.upgrade_button=self.button(actions,'Upgrade to L2',self.upgrade,padx=5)
        self.upgrade_button.pack(side='left',fill='x',expand=True)
        self.pause_button=self.button(self.construction_panel,'Pause production',self.toggle_facility,pady=4)
        self.pause_button.pack(fill='x',pady=(0,3))
        self.production_hint=self.label(self.construction_panel,fg=ACCENT,anchor='w',justify='left',wraplength=440,font=('Segoe UI',9))
        self.production_hint.pack(fill='x')
        self.build_hint=self.label(self.construction_panel,anchor='w',justify='left',wraplength=440,fg=MUTED,font=('Segoe UI',9))
        self.build_hint.pack(fill='x',pady=(4,5))
        self.council_separator=tk.Frame(right,bg='#3a526d',height=1);self.council_separator.pack(fill='x')
        self.event_title=self.label(right,anchor='w',fg='#f0ce8b',font=('Segoe UI',12,'bold'),wraplength=440)
        self.event_title.pack(fill='x',pady=(6,4))
        self.event_story=self.label(right,anchor='nw',justify='left',wraplength=440,font=('Segoe UI',10));self.event_story.pack(fill='x')
        self.event_scale=self.label(right,anchor='w',justify='left',fg=MUTED,wraplength=440,font=('Segoe UI',9))
        self.event_scale.pack(fill='x',pady=(5,0))
        self.event_buttons=[]
        for index in range(2):
            button=self.button(right,'',lambda i=index:self.resolve(i),anchor='w',justify='left',wraplength=420,
                font=('Segoe UI',9),highlightthickness=1,highlightbackground='#4c6b82',bg='#233f55')
            button.pack(fill='x',pady=(6,0));self.event_buttons.append(button)
        def wheel(event):
            self.detail_canvas.yview_scroll(-int(event.delta/120),'units');return 'break'
        def bind_wheel(widget):
            widget.bind('<MouseWheel>',wheel,add='+')
            for child in widget.winfo_children():bind_wheel(child)
        bind_wheel(detail)

    def _fit_right_panel(self, event):
        self.detail_canvas.configure(scrollregion=self.detail_canvas.bbox("all"))
        width = max(200, event.width - 24)
        for label in (self.selection_label, self.build_hint, self.event_story, self.event_title, self.event_scale, self.production_hint):
            label.configure(wraplength=width)
        for button in self.event_buttons:
            button.configure(wraplength=width - 20)

    def select_tile(self, row, column):
        self.selected = (row, column)
        self.refresh()

    def _draw_board(self):
        draw_board(self.board, self.game, self.selected,
                   {"muted": MUTED, "accent": ACCENT}, self.kind.get(), self.tr,
                   self.chinese_font if self.language == "zh_CN" else "Segoe UI")

    def _click_map(self, event):
        self.board.focus_set()
        row = int(event.y * SIZE / max(1, self.board.winfo_height()))
        column = int(event.x * SIZE / max(1, self.board.winfo_width()))
        if 0 <= row < SIZE and 0 <= column < SIZE:
            self.select_tile(row, column)

    def _move_selection(self, dr, dc):
        row, column = self.selected
        self.select_tile(max(0, min(SIZE - 1, row + dr)), max(0, min(SIZE - 1, column + dc)))
        return "break"

    def refresh(self):
        game = self.game
        if self._render_ruleset != game.ruleset:
            self._cancel_effects()
            self._render_ruleset = game.ruleset
            for widget in self._text_widgets:
                widget.retranslate()
        self.motion_button.configure(text="Motion: reduced" if self.reduce_motion else "Motion: on")
        self.sound_button.configure(text="Sound: unavailable" if not self.sound.available else "Sound: on" if self.sound.enabled else "Sound: off")
        self.beacon_progress.delete('all')
        for stage in range(3):
            self.beacon_progress.create_rectangle(2 + stage * 21, 5, 18 + stage * 21, 20,
                outline=ACCENT, fill=ACCENT if game.beacon_stage > stage else PANEL)
        self.day_label.configure(text=f"Day {game.day:02d} / {game.campaign_days}")
        self.mission_label.configure(text=game.mission_summary())
        if game.ruleset in ('v32', 'v33'):
            objective = game.objective_status()
            self.mission_label.configure(text=objective['text'], fg='#ffc0a7' if objective['state'] == 'impossible'
                or game.day >= 26 and game.beacon_stage < 3 else '#f0ce8b' if objective['state'] == 'ready' else ACCENT)
            self.beacon_button.configure(bg='#286e68' if objective['state'] == 'ready' else '#2b4761')
        self.beacon_button.configure(state="disabled" if game.beacon_error() else "normal")
        self.ration_button.configure(text=f"Emergency rations ({2 - game.ration_uses} left)",
                                     state="disabled" if game.ration_error() else "normal")
        if game.ration_days:
            self.ration_button.configure(text=f'Rations ACTIVE: settlement {game.day + 1} ({2-game.ration_uses} left)')
        self.crew_label.configure(text=game.crew_message())
        self.crew_icons.delete("all")
        for index in range(min(game.population, 18)):
            x = 5 + index * 8
            self.crew_icons.create_oval(x, 2, x + 5, 7, fill=ACCENT, outline="")
            self.crew_icons.create_line(x + 2, 8, x + 2, 18, fill=ACCENT, width=3)
        for name, widget in self.metrics.items():
            suffix = f" / {game.housing}" if name == "population" else ""
            widget.configure(text=f"{name.title()}  {getattr(game, name)}{suffix}")
        self.happiness_label.configure(text=f"Happiness {game.happiness}/100")
        self.happiness_bar.delete("all")
        self.happiness_bar.create_rectangle(0, 0, 1.5 * game.happiness, 10, outline="",
            fill=ACCENT if game.happiness >= 65 else "#e6b655" if game.happiness >= 40 else "#ef968b")
        forecast = game.forecast()
        for name, trend in self.metric_trends.items():
            value = forecast[name]
            trend.configure(text=f"Next week {value:+d}" if game.ruleset in ('v31', 'v32', 'v33') else f"Next day {value:+d}",
                            fg=ACCENT if value >= 0 else '#f4a698')
        self.forecast_label.configure(text=f"Meals: {game.food_demand}/day; offline: {forecast['offline']}. {forecast['growth_reason']}\n"
            f"Active effects: {game.effects_summary()}. Forecast includes growth; excludes new council choices.")
        from chronicle import latest
        week,story=latest(game)
        self.chronicle_title.configure(text='COLONY CHRONICLE' if week is None else f'COLONY CHRONICLE / Week {week}')
        self.chronicle_text.configure(text=story)
        self.chronicle_frame.configure(bg='#203c49')
        if game.status != "active":
            self.forecast_label.configure(text=f"Expedition complete. {game.result()[0]} | Score {game.result()[1]}")
        self.feedback_label.configure(text=self.feedback)
        self._draw_board()
        row, column = self.selected
        tile = game.grid[row][column]
        self.site_hint.configure(text=game.placement_info(row, column, tile or self.kind.get()))
        tile_name = "Headquarters" if tile == "hq" else BUILDINGS.get(tile, {}).get("name", "Empty ground")
        level = game.levels[row][column]
        details = "One build OR upgrade per day. No demolition."
        if tile is None:
            selected_kind = self.kind.get()
            details = f"Build L1: {facility_effect(selected_kind, 1, game.campaign_days)}\nOne build OR upgrade per day."
        if tile in BUILDINGS:
            details = f"L{level}: {facility_effect(tile, level, game.campaign_days)}"
            if level == 1:
                details += f"\nUpgrade: {UPGRADE_COSTS[tile]} Materials -> {facility_effect(tile, 2, game.campaign_days)}"
        if game.ruleset in ('v32', 'v33'):
            details=details.replace('One build OR upgrade per day.', 'Build / upgrade / HQ share one crew action.')
        self.selection_label.configure(text=f"Tile {chr(65 + row)}{column + 1}: {tile_name}\n{details}")
        cost = BUILDINGS[self.kind.get()]["cost"]
        hint = "Ready to build."
        if game.status != "active":
            hint = "Expedition complete. Start New or Load to continue playing."
        elif game.pending_event:
            hint = "Council decision required first."
        elif tile is not None:
            hint = "Select an empty tile to build."
        elif game.built_today:
            hint = "Construction used. Advance one day for a fresh crew."
        elif game.materials < cost:
            hint = f"Need {cost} Materials; {game.materials} available."
        upgrade_error = game.upgrade_error(row, column)
        self.build_hint.configure(text=hint if hint != "Ready to build." else "Select an empty tile to build, or a facility to upgrade.")
        self.build_button.configure(state="normal" if hint == "Ready to build." else "disabled")
        self.upgrade_button.configure(text=f"Upgrade: {UPGRADE_COSTS[tile]} Materials" if tile in BUILDINGS and level == 1
                                      else "Maximum level (L2)" if level == 2 else "Upgrade to L2",
                                      state="disabled" if upgrade_error else "normal")
        if tile in BUILDINGS and upgrade_error:
            self.build_hint.configure(text=upgrade_error)
        error=game.pause_error(row,column)
        self.pause_button.configure(text='Resume production' if game.paused[row][column] else 'Pause production',state='disabled' if error else 'normal')
        self.production_hint.configure(text=error if error else game.facility_status(row,column)+'\n'+
            'Paused: no power or output. No crew action; timers continue.')
        self.next_button.configure(state="normal" if game.status == "active" and not game.pending_event else "disabled")
        self._refresh_council()
        if getattr(self,'_shown_pending',None) != game.pending_event:
            self.detail_canvas.yview_moveto(0)
            self._shown_pending=game.pending_event
    def _refresh_council(self):
        game = self.game
        if game.pending_event or game.status != "active":
            self.construction_panel.pack_forget()
        elif not self.construction_panel.winfo_manager():
            self.construction_panel.pack(before=self.council_separator, fill="x")
        for button in self.event_buttons:
            button.pack_forget()
        self.event_scale.configure(text="")
        if game.status != "active":
            title, score = game.result()
            self.event_title.configure(text=f"{'SURVIVED' if game.status == 'won' else 'COLONY LOST'}  /  {title}")
            self.event_story.configure(text=f"{game.reason}\nScore: {score} | Survivors: {game.population}\n"
                                           f"{game.summary()}\n"
                                           "Review the log, save this ending, or start New.")
            if game.ruleset in ('v32', 'v33'):
                memories='\n'.join(game.memory_summary().splitlines()[:2])
                self.event_story.configure(text=f"{game.reason}\nScore: {score} | Survivors: {game.population}\n"
                    f"{memories}\nOpen Report for the colony record and rating targets.")
        elif game.pending_event:
            event = game.event_view()
            self.event_title.configure(text=f"COUNCIL  /  {event['title']}")
            self.event_story.configure(text=event["story"])
            if game.ruleset in ("v31", "v32", "v33"):
                self.event_scale.configure(text="Opening costs unchanged." if game.day < 9 else
                    "Cost locked on arrival; scales with week and population, never inventory.")
                if game.ruleset in ('v32', 'v33'):
                    self.event_scale.configure(text='Locked quote. No inventory tax.')
            for index, button in enumerate(self.event_buttons):
                option = event["options"][index]
                error = game.option_error(index)
                text = f"{index + 1}. {option['label']}\n{describe_option(option)}"
                if error:
                    text += f"  [Unavailable: {error}]"
                elif game.ruleset in ('v32', 'v33'):
                    preview=game.preview_choice(index)
                    text += ('\nThis choice ends the colony.' if preview.get('ended') else
                             f"\nNext: Food {preview['food']:+d}, Energy {preview['energy']:+d}; losses {preview['deaths']}.")
                button.configure(text=text, state="disabled" if error else "normal")
                button.pack(fill="x", pady=(6, 0))
        else:
            self.event_title.configure(text="COUNCIL  /  Standing by")
            self.event_story.configure(text=("Legacy: six events over 15 days." if game.campaign_days == 15 else
                "Next encounter: Day " + str(next(day for day in game.event_days if day > game.day)) + "."
                if game.day < game.event_days[-1] else "All encounters resolved. Finish the beacon."))

    def toggle_facility(self):
        self._action(lambda:self.game.toggle_facility(*self.selected))
        if self.game.pause_error(*self.selected) is None:
            self.feedback=self.game.log[-1]
            self.refresh()

    def show_history(self):
        from chronicle import entries
        records=entries(self.game)
        lines=[(('COLONY CHRONICLE' if week is None else f'COLONY CHRONICLE / Week {week}')+'\n'+story)
               for week,story in records]
        self._info('Colony history','\n\n'.join(lines)+'\n\n'+self.game.memory_summary()+
                   '\n\n'+ '\n'.join(self.game.log),parent=self.root)

    def show_report(self):
        self._info("Colony report", self.game.last_report + "\n\n" + self.game.planning_report()
                   + "\n\n" + self.game.summary() + "\n\n" + self.game.memory_summary(), parent=self.root)

    def show_guide(self):
        if self.game.campaign_days == 15:
            self._info("Governor's guide",
                "Survive 15 settled days. Build OR upgrade once per day.\n"
                "Legacy: six events over 15 days.\n"
                "Each person eats 1 Food/day. Each Home uses 1 Energy/day.\n"
                "Power order: HQ, homes, farms, then mines.\n"
                "Growth every third day needs housing, powered homes, surplus food and Happiness 40+.\n"
                "Legacy expedition: the beacon objective is not required.\n"
                "NEXT: OFFLINE is a power forecast. Report shows the full calculation.", parent=self.root)
            return
        if self.game.ruleset in ('v31', 'v32', 'v33'):
            if self.game.ruleset in ('v32', 'v33'):
                self._info("Governor's guide",
                    "Thirty weeks to make a home. Survive AND complete beacon 3/3.\n"
                    "One crew action each week: build, upgrade OR HQ work.\n"
                    "HQ unlocks after weeks 6/14/22: 18/28/36 Materials + 8/18/32 Energy.\n"
                    "Finish the beacon by Week 29, before advancing into Week 30.\n\n"
                    + ('Pause/resume Farms or Mines without a crew action. Paused sites use no power and produce nothing; timers continue.\n\n'
                       if self.game.ruleset == 'v33' else '')
                    + self.game.ration_help() + "\n\n"
                    "Meals: 1 Food/person/week; Homes: 1 Energy/week. Growth checks every4 weeks.\n"
                    "A powered Farm beside a Home gets +2 Food; Home beside Mine causes noise.\n"
                    "First eight weeks keep V3.0 economics and two opening events.\n"
                    "Council weeks: 2,5,9,12,14,16,18,20,22,24,26,28.\n"
                    "V3.2 late choices: arrivals bring 6 Materials; converter repair gives 4 Energy; full community supply gives 12 Happiness.\n"
                    "Late cost weights: Immigration F1; Fault M1; Community F2/E1. Other weights unchanged.\n"
                    "Week21+: add3 to each up-front resource cost. Inventory never raises costs.\n"
                    "Costs lock when the event arrives; second choices require no up-front payment.\n"
                    "Cold: Farms75% for2 weeks; dust: Solar50% for3; filters: Farm/Mine power+1 for3.\n"
                    "Read the forecast after every choice; Report explains all active effects.\n\n"
                    + self.game.memory_summary() + "\n\n"
                    "Sound starts off; Motion can be reduced. Both settings leave rules unchanged.",parent=self.root)
                return
            self._info("Governor's guide",
                "Thirty weeks to make a home. Survive AND complete beacon 3/3.\n"
                "One crew action each week: build, upgrade OR HQ work.\n"
                "HQ unlocks after weeks 6/14/22: 18/28/36 Materials + 8/18/32 Energy.\n"
                "First eight weeks keep V3.0 economics and two opening events.\n"
                "Council weeks: 2,5,9,12,14,16,18,20,22,24,26,28.\n"
                "Week9+: first-option cost = base + Population x resource weight.\n"
                "Week21+: add3 to each up-front resource cost. Inventory never raises costs.\n"
                "Weights (Food/Energy/Materials; omitted resources have no cost):\n"
                "Storm M2; Immigration F2; Fault M2; Contamination E2; Deposit E1/M1.\n"
                "Protest F2; Medical E1/M1; Festival F2/E1; Cold E2; Dust M2.\n"
                "Filters E1/M1; Community F3/E1. See each locked offer before choosing.\n"
                "Costs lock when the event arrives; second choices require no up-front payment.\n"
                "Cold: Farms75% for2 weeks; dust: Solar50% for3; filters: Farm/Mine power+1 for3.\n"
                "Solar storm/dust reductions never multiply. Production crises are spaced apart.\n"
                "Meals: 1 Food/person/week; Homes: 1 Energy/week. Growth checks every4 weeks.\n"
                "A powered Farm beside a Home gets +2 Food; Home beside Mine causes noise.\n"
                "Two ration orders: next meals halved (round up), Happiness-8, no growth.\n"
                "Read the forecast after every choice; Report explains all active effects.\n"
                "Sound starts off; Motion can be reduced. Both settings leave rules unchanged.", parent=self.root)
            return
        self._info("Governor's guide",
            "Survive 30 days AND finish all three HQ beacon stages.\n"
            "One daily crew action: build, upgrade OR HQ work.\n"
            "HQ unlocks after days 6, 14, 22; costs 18/28/36 Materials and 8/18/32 Energy.\n"
            "HQ work gives +3 Happiness per stage (cap 100).\n"
            "Rations: twice per game, next meals halved (round up), -8 Happiness, no growth that day.\n\n"
            "Each person eats 1 Food/day. Each Home uses 1 Energy/day.\n"
            "Power order: HQ, homes, farms, then mines.\n\n"
            "Orthogonal neighbours only (not diagonals):\n"
            "- A powered Farm next to any Home gets +2 Food/day, once per Farm.\n"
            "- Each Home next to any Mine causes -2 Happiness/day; total noise capped at -4.\n"
            "Green/orange borders preview these links around your selected tile.\n\n"
            "Growth every fourth day needs housing, powered homes, surplus food and Happiness 40+.\n"
            "Quiet days move Happiness one point toward 78; events can raise it higher.\n"
            "Legacy imports keep 15 days, six events, third-day growth and their original Happiness recovery.\n"
            "Storms and rover extraction can affect the NEXT 2 or 3 settlements.\n"
            "Read both choices. Late investments may not pay back.\n"
            "NEXT: OFFLINE is a power forecast. Report shows the full calculation.", parent=self.root)

    def _action(self, callback):
        self._cancel_effects()
        old_grid = [row[:] for row in self.game.grid]
        old_levels = [row[:] for row in self.game.levels]
        old_beacon, old_pending, old_status = self.game.beacon_stage, self.game.pending_event, self.game.status
        old_turn, old_orders = self.game.day, self.game.ration_uses
        old_danger = self.game.forecast()['food_shortfall'] > 0
        before = {key: getattr(self.game, key) for key in ("food", "energy", "materials", "population", "happiness")}
        succeeded = False
        try:
            callback()
        except RuleError as exc:
            self.feedback=str(exc)
        else:
            succeeded = True
            delta = "   |   ".join(f"{key.title()} {getattr(self.game, key) - value:+d}"
                                    for key, value in before.items() if getattr(self.game, key) != value)
            self.feedback = "Last action: " + (delta or "No stored-resource change.")
        self.refresh()
        if not succeeded:
            return
        changed = old_grid != self.game.grid or old_levels != self.game.levels
        if self.game.status != old_status:
            self.sound.play('victory' if self.game.status == 'won' else 'failure')
        elif self.game.beacon_stage > old_beacon:
            self.sound.play('beacon')
        elif self.game.pending_event and self.game.pending_event != old_pending:
            self.sound.play('event')
        elif self.game.forecast()['food_shortfall'] > 0 and not old_danger:
            self.sound.play('warning')
        elif changed:
            self.sound.play('build')
        elif self.game.ration_uses > old_orders:
            self.sound.play('ration')
        elif old_pending and not self.game.pending_event:
            self.sound.play('choice')
        elif self.game.day != old_turn:
            self.sound.play('warning' if self.game.day in (26,28,29) and self.game.beacon_stage < 3 else 'settle')
        if not self.sound.available:
            self.sound_button.configure(text='Sound: unavailable')
        if self.reduce_motion:
            return
        for index, name in enumerate(('food', 'energy', 'materials')):
            delta = getattr(self.game, name) - before[name]
            if not delta:
                continue
            label = tk.Label(self.metrics_frame, text=f'{delta:+d}', bg='#29485b',
                             fg=ACCENT if delta > 0 else '#ffc0a7', font=('Segoe UI', 10, 'bold'), padx=3)
            self._float_labels.append(label)
            for step in range(8):
                self._schedule(step * 90, lambda w=label, n=index, s=step:
                               w.place(relx=(n + .97) / 4, y=8-s, anchor='ne'))
        self._schedule(800, self._clear_floats)
        if changed:
            row, column = self.selected
            width, height = self.board.winfo_width()/SIZE, self.board.winfo_height()/SIZE
            self.board.create_rectangle(column*width+3, row*height+3, (column+1)*width-3, (row+1)*height-3,
                                        outline='#ffe6a8', width=3, tags='action_flash')
            self._schedule(350, lambda: self.board.delete('action_flash'))
        if old_beacon < 3 and self.game.beacon_stage == 3 or self.game.day != old_turn and self.game.day in (6,14,22):
            for step in range(6):
                self._schedule(step * 150, lambda s=step: self.mission_frame.configure(bg='#36736f' if s % 2 == 0 else PANEL))

    def _clear_floats(self):
        for label in self._float_labels:
            label.destroy()
        self._float_labels.clear()

    def build(self):
        row, column = self.selected
        self._action(lambda: self.game.build(row, column, self.kind.get()))

    def advance(self):
        if self.game.ruleset in ('v31','v32','v33') and self.game.status == 'active' and not self.game.pending_event and self.game.day == 29 and self.game.beacon_stage < 3:
            if not self._ask('Signal deadline',
                'Advancing into Week 30 without beacon 3/3 ends this expedition as Stranded Colony.\n'
                'Return to inspect the colony, or continue knowing the outcome. No automatic repair is performed.',
                parent=self.root,confirm_label=self.tr('Continue anyway')):
                return
        self._action(self.game.next_day)

    def use_rations(self):
        preview=self.game.ration_preview()
        if 'error' in preview:
            self.feedback=preview['error'];self.refresh();return
        if not self.ration_explained:
            message=(self.game.ration_help()+f"\n\nRation settlement: Day {preview['turn']}.\n"
                f"Meals {preview['meals_before']} -> {preview['meals_after']}; Happiness {preview['happiness_before']} -> {preview['happiness_after']}.\n"
                f"Expected losses {preview['deaths_before']} -> {preview['deaths_after']}.\n"
                f"Orders remaining before use: {preview['remaining']}.\nCancel leaves resources and remaining orders unchanged.")
            if not self._ask('Ration preview',message,parent=self.root,confirm_label=self.tr('Activate rations')):
                return
            self.ration_explained=True
        self._action(self.game.emergency_rations)

    def upgrade(self):
        self._action(lambda: self.game.upgrade(*self.selected))

    def resolve(self, index):
        self._action(lambda: self.game.choose_event(index))

    def _restart(self, seed):
        if self._ask("New colony", "Replace the current colony? Save first if you want to keep it.", parent=self.root):
            self._cancel_effects()
            dialogs.close_readers(self.root)
            self.game = Game(seed=seed)
            self.ration_explained=False
            self.selected = (0, 0)
            self.feedback = "New expedition. One construction action per day: build OR upgrade."
            self.refresh()

    def new_game(self):
        self._restart(None)

    def demo_game(self):
        # A reproducible normal game, with the same resources and rules.
        self._restart(7)

    def save(self):
        filename = filedialog.asksaveasfilename(parent=self.root, title=self.tr("Save colony"),
            initialfile="colony_v33_save.json", defaultextension=".json",
            filetypes=[(self.tr("Colony JSON save"), "*.json"), (self.tr("All files"), "*.*")])
        if not filename:
            return
        try:
            save_game(self.game, filename)
        except SaveError as exc:
            self._error("Save failed", str(exc), parent=self.root)
        else:
            self._info("Colony saved", f"Saved to {Path(filename).name}", parent=self.root)

    def load(self):
        filename = filedialog.askopenfilename(parent=self.root, title=self.tr("Load colony"),
            filetypes=[(self.tr("Colony JSON save"), "*.json"), (self.tr("All files"), "*.*")])
        if not filename:
            return
        try:
            candidate = load_game(filename)
        except SaveError as exc:
            self._error("Load failed", f"{exc}\nYour current colony is unchanged.", parent=self.root)
            return
        prompt = "Replace the current colony with this save? Unsaved progress will be lost."
        if candidate.ruleset not in ('v31', 'v32', 'v33'):
            prompt += "\nLegacy rules: original days and event deck preserved."
            if candidate.imported_from_v1:
                prompt += " Buildings start at L1, Happiness at 70."
        if self._ask("Load colony", prompt, parent=self.root):
            self._cancel_effects()
            dialogs.close_readers(self.root)
            self.game = candidate
            self.ration_explained=False
            self.selected = (0, 0)
            self.feedback = "Loaded colony. Future event order and construction availability restored."
            self.refresh()

    def close(self):
        if self._ask("Leave Colony Zero", "Quit? Unsaved progress will be lost.", parent=self.root):
            self._cancel_effects()
            dialogs.close_readers(self.root)
            self.sound.stop()
            self.root.destroy()
