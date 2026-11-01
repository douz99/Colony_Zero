"""Colony Zero V3.3: explicit production choices and compatible weekly rules."""

from collections import Counter
import random

from copy import deepcopy
from events import EFFECTS, EVENTS, offer_options

SIZE = 5
LAST_DAY = 30
EVENT_DAYS = (2, 5, 9, 12, 14, 16, 18, 20, 22, 24, 26, 28)
V30_EVENT_DAYS = (2, 5, 9, 13, 17, 21, 25, 28)
V30_EVENTS = ("storm", "immigrants", "fault", "contamination", "deposit", "protest", "medical", "festival")
LEGACY_EVENT_DAYS = (2, 4, 6, 9, 12, 14)
LEGACY_EVENTS = ("storm", "immigrants", "fault", "contamination", "deposit", "protest")
# Each HQ stage spends the same daily construction action as a facility.
BEACON_STAGES = ((6, 18, 8), (14, 28, 18), (22, 36, 32))
RESOURCE_LIMIT = 999


def empty_memories():
    return {"home_week": None, "beacon_week": None, "welcomed": 0, "ration_rescues": 0}
BUILDINGS = {
    "solar": {"name": "Solar Plant", "symbol": "SOL", "cost": 10,
              "effect": "+7 Energy/day", "color": "#e6b655"},
    "farm": {"name": "Hydroponic Farm", "symbol": "FARM", "cost": 12,
             "effect": "3 Energy -> 6 Food/day", "color": "#72c99b"},
    "mine": {"name": "Mining Facility", "symbol": "MINE", "cost": 14,
             "effect": "3 Energy -> 6 Materials/day", "color": "#b49ddb"},
    "home": {"name": "Residential Module", "symbol": "HOME", "cost": 12,
             "effect": "+4 housing; 1 Energy/day", "color": "#7cbcea"},
}

# Only four facility types; each can be upgraded exactly once.
UPGRADE_COSTS = {"solar": 8, "farm": 10, "mine": 10, "home": 8}
OUTPUTS = {
    "solar": {1: (0, 7), 2: (0, 12)},
    "farm": {1: (3, 6), 2: (4, 9)},
    "mine": {1: (3, 6), 2: (4, 9)},
    "home": {1: (1, 4), 2: (1, 6)},
}


def facility_effect(kind, level, campaign_days=LAST_DAY):
    energy, output = OUTPUTS[kind][level]
    if kind == "farm" and campaign_days == 15:
        output = 8 if level == 1 else 12
    if kind == "solar":
        return f"+{output} Energy/day"
    if kind == "home":
        return f"+{output} housing; 1 Energy/day"
    return f"{energy} Energy -> {output} {'Food' if kind == 'farm' else 'Materials'}/day"


class RuleError(ValueError):
    """A rejected player action; the caller can show its message safely."""


class Game:
    """One colony. Day counts completed settlements, starting at zero."""

    def __init__(self, seed=None, campaign_days=LAST_DAY, ruleset=None):
        if type(campaign_days) is not int or campaign_days not in (15, 30):
            raise ValueError("Campaign length must be 15 or 30 days.")
        self.campaign_days = campaign_days
        self.ruleset = ruleset or ("v20" if campaign_days == 15 else "v33")
        if self.ruleset not in ("v20", "v30", "v31", "v32", "v33") or (self.ruleset == "v20") != (campaign_days == 15):
            raise ValueError("Campaign length and ruleset do not match.")
        self.event_snapshot = None
        self.story_seed = random.Random(seed).randrange(2**31) if self.ruleset in ('v32', 'v33') else 0
        self.memories = empty_memories()
        self.bulletins_seen = []
        self.paused = [[False for _ in range(SIZE)] for _ in range(SIZE)]
        self.beacon_stage = 0
        self.ration_uses = 0
        self.ration_days = 0
        # Each row is a separate list: editing one tile cannot change another row.
        self.grid = [[None for _ in range(SIZE)] for _ in range(SIZE)]
        self.levels = [[0 for _ in range(SIZE)] for _ in range(SIZE)]
        self.grid[2][2] = "hq"
        self.food = 20
        self.energy = 12
        self.materials = 42
        self.population = 4
        self.happiness = 70
        self.day = 0
        self.built_today = False
        self.status = "active"
        self.reason = ""
        self.pending_event = None
        self.effects = {}
        self.last_report = "No days settled yet. Each resident needs 1 Food per day."
        self.imported_from_version = None
        # Save the whole shuffled deck, so loading cannot reroll future events.
        self.event_order = list(LEGACY_EVENTS if campaign_days == 15 else V30_EVENTS)
        rng = random.Random(seed)
        rng.shuffle(self.event_order)
        if self.ruleset in ("v31", "v32", "v33"):
            opening = self.event_order[:2]
            remaining = self.event_order[2:]
            rng.shuffle(remaining)
            weather = ["cold", "dust", "filters"]
            rng.shuffle(weather)
            deck = [None] * 12
            deck[:2] = opening
            for slot, event in zip((2, 5, 8), weather):
                deck[slot] = event
            deck[11] = "community"
            if "storm" in remaining:
                deck[3] = "storm"
                remaining.remove("storm")
            for slot in range(12):
                if deck[slot] is None:
                    deck[slot] = remaining.pop()
            self.event_order = deck
        self.log = ["Landing complete. Four pioneers. Fifteen days. One chance." if campaign_days == 15
                    else "Four pioneers. Thirty days. Repair the beacon before the ship passes."]
        if self.ruleset in ("v31", "v32", "v33"):
            self.log = ["Four pioneers step into the dust. Thirty weeks to light a way home."]
            self.last_report = "No weeks settled yet. Each resident needs 1 Food per week."

    def time_text(self, text):
        if self.ruleset not in ("v31", "v32", "v33"):
            return text
        import re
        words = {"Day": "Week", "day": "week", "days": "weeks", "Days": "Weeks",
                 "daily": "weekly", "today": "this week"}
        return re.sub(r"\b(Day|day|days|Days|daily|today)\b", lambda m: words[m[0]], text)

    def event_options(self):
        if self.event_snapshot is not None:
            return deepcopy(self.event_snapshot["options"])
        return deepcopy(EVENTS[self.pending_event]["options"]) if self.pending_event else []

    def event_view(self):
        event = deepcopy(EVENTS[self.pending_event])
        if self.ruleset in ("v31", "v32", "v33"):
            from narrative import STORIES
            event.update(title=STORIES[self.pending_event][0], story=STORIES[self.pending_event][2])
        if self.ruleset in ('v32', 'v33'):
            from polish import STORY_VARIANTS
            variant = STORY_VARIANTS.get(self.pending_event)
            if variant and (self.story_seed + self.event_order.index(self.pending_event)) % 2:
                event.update(title=variant[0], story=variant[2])
        event["options"] = self.event_options()
        return event

    def preview_choice(self, index):
        """Evaluate a real choice on a detached state; never reroll or mutate play."""
        error = self.option_error(index)
        if error:
            return {"error": error}
        candidate = deepcopy(self)
        candidate.choose_event(index)
        if candidate.status != 'active':
            return {"ended": True, "status": candidate.status}
        return {"ended": False, **candidate.forecast()}

    def ration_preview(self):
        error = self.ration_error()
        if error:
            return {"error": error}
        before = self.forecast()
        candidate = deepcopy(self)
        candidate.emergency_rations()
        after = candidate.forecast()
        return {"turn": self.day + 1, "meals_before": self.food_demand,
                "meals_after": candidate.food_demand, "happiness_before": self.happiness,
                "happiness_after": candidate.happiness, "deaths_before": before['deaths'],
                "deaths_after": after['deaths'], "remaining": 2 - self.ration_uses}

    def ration_help(self):
        text = ("Next settlement only: meals halved (round up), Happiness -8, no growth.\n"
                "Two orders per expedition. No crew action. No Food is created.")
        error = self.ration_error()
        return text + ("\n" + error if error else "")

    def objective_status(self):
        """A public objective explanation, including available crew opportunities."""
        if self.campaign_days == 15:
            return {"state": "legacy", "text": "Legacy expedition: the beacon objective is not required."}
        if self.status != 'active':
            return {"state": "ended", "text": "Expedition complete. Start New or Load to continue playing."}
        if self.beacon_stage == 3:
            return {"state": "complete", "text": "Goal: survive to Week 30. Beacon 3/3 READY."}
        unlock, materials, energy = BEACON_STAGES[self.beacon_stage]
        opportunities = max(0, self.campaign_days - self.day - int(self.built_today))
        missing = 3 - self.beacon_stage
        if missing > opportunities:
            state, detail = 'impossible', 'Too few crew opportunities remain.'
        elif self.day < unlock:
            state, detail = 'locked', f'Unlock: Week {unlock}.'
        elif self.pending_event:
            state, detail = 'council', 'Council decision required first.'
        elif self.built_today:
            state, detail = 'crew', 'Daily crew action used today.'
        elif self.materials < materials or self.energy < energy:
            state, detail = 'supplies', f'Need {max(0, materials-self.materials)} more Materials / {max(0, energy-self.energy)} more Energy.'
        else:
            state, detail = 'ready', 'READY TO REPAIR'
        text = (f'Goal: survive + Beacon {self.beacon_stage}/3 | {materials}M + {energy}E | '
                f'{detail} By Week 29.')
        return {"state": state, "text": text, "remaining_stages": missing,
                "opportunities": opportunities, "materials": materials, "energy": energy}

    @property
    def event_days(self):
        return LEGACY_EVENT_DAYS if self.campaign_days == 15 else V30_EVENT_DAYS if self.ruleset == "v30" else EVENT_DAYS

    @property
    def growth_interval(self):
        return 3 if self.campaign_days == 15 else 4

    def beacon_error(self):
        try:
            self._require_active()
        except RuleError as exc:
            return str(exc)
        if self.campaign_days == 15:
            return "Legacy expedition: the beacon objective is not required."
        if self.beacon_stage == 3:
            return "Beacon ready. Keep the colony alive until Day 30."
        day, materials, energy = BEACON_STAGES[self.beacon_stage]
        if self.day < day:
            return f"Next beacon stage unlocks after Day {day}."
        if self.built_today:
            return "The crew is busy. HQ work shares the daily construction action."
        if self.materials < materials:
            return f"Need {materials} Materials; only {self.materials} available."
        if self.energy < energy:
            return f"Need {energy} Energy; only {self.energy} available."
        return None

    def repair_beacon(self):
        """Charge only after every rule passes; never grant free objective progress."""
        error = self.beacon_error()
        if error:
            raise RuleError(error)
        _, materials, energy = BEACON_STAGES[self.beacon_stage]
        self.materials -= materials
        self.energy -= energy
        self.beacon_stage += 1
        if self.ruleset in ('v32', 'v33') and self.beacon_stage == 3:
            self.memories['beacon_week'] = self.day
        self.built_today = True
        self.happiness = min(100, self.happiness + 3)
        self._record(f"Beacon stage {self.beacon_stage}/3 complete: -{materials} Materials, -{energy} Energy; Happiness +3 (cap 100).")
        if self.ruleset in ('v31', 'v32', 'v33'):
            self._record(("The first test leaves a clear line in the noise.",
                          "Someone pins the ship's approach time beside the radio.",
                          "Three green lights. At last, this place has a voice.")[self.beacon_stage - 1])

    def ration_error(self):
        try:
            self._require_active()
        except RuleError as exc:
            return str(exc)
        if self.ration_days:
            return "Emergency rationing is already active for the next settlement."
        if self.ration_uses >= 2:
            return "Both emergency ration orders have been used."
        return None

    def emergency_rations(self):
        """Two orders per expedition; no construction action or created food."""
        error = self.ration_error()
        if error:
            raise RuleError(error)
        self.ration_uses += 1
        self.ration_days = 1
        self.happiness = max(0, self.happiness - 8)
        self._record("Emergency rations: next meals halved (round up), growth paused; Happiness -8 (floor 0).")

    def mission_summary(self):
        if self.campaign_days == 15:
            return "Legacy expedition: survive 15 days; beacon not required."
        if self.beacon_stage == 3:
            return "Beacon 3/3 READY | Survive until Day 30."
        day, materials, energy = BEACON_STAGES[self.beacon_stage]
        return f"Beacon {self.beacon_stage}/3 | Next: {materials} Materials + {energy} Energy | Unlock: Day {day} | Deadline: Day 30"

    def crew_message(self):
        if self.population == 0:
            return "The crew channel is silent."
        if self.status == "lost":
            return "We survived, but the ship never received our coordinates."
        forecast = self.forecast()
        if forecast["food_shortfall"]:
            return "Our next meal is at risk. Can we ration or power a farm?"
        if forecast["offline"]:
            return "The lights are going out. Check our power supply."
        if self.day >= 22 and self.campaign_days == 30 and self.beacon_stage < 3:
            return "The ship is getting close. Please finish the beacon."
        if self.happiness < 40:
            return "We need hope before more people can settle here."
        return "This is becoming a place we can call home."

    def pause_error(self, row, column):
        try:
            self._require_active()
            self._check_tile(row, column)
        except RuleError as exc:
            return str(exc)
        if self.ruleset != 'v33':
            return 'Production controls require a new V3.3 expedition.'
        if self.grid[row][column] not in ('farm', 'mine'):
            return 'Only Farms and Mines can be paused.'
        return None

    def toggle_facility(self, row, column):
        """No crew/payment: only the final switch state affects settlement."""
        error = self.pause_error(row, column)
        if error:
            raise RuleError(error)
        self.paused[row][column] = not self.paused[row][column]
        state = 'PAUSED' if self.paused[row][column] else 'RUNNING'
        self._record(f'Production {chr(65+row)}{column+1}: {state}.')

    def facility_status(self, row, column):
        self._check_tile(row, column)
        if self.grid[row][column] not in ('farm', 'mine'):
            return ''
        if self.paused[row][column]:
            return 'PAUSED BY YOU'
        if (row, column) in self.forecast()['offline_tiles']:
            return 'NEXT: OFFLINE'
        return 'RUNNING'

    def counts(self):
        """Count facilities from the map rather than duplicating mutable data."""
        return Counter(tile for row in self.grid for tile in row if tile in BUILDINGS)

    @property
    def housing(self):
        return 6 + sum(OUTPUTS["home"][self.levels[r][c]][1]
                       for r in range(SIZE) for c in range(SIZE) if self.grid[r][c] == "home")

    @property
    def upgrade_count(self):
        return sum(level == 2 for row in self.levels for level in row)

    @property
    def food_demand(self):
        return (self.population + 1) // 2 if self.ration_days else self.population

    @staticmethod
    def neighbors(row, column):
        """Four orthogonal neighbours only; edges never wrap or use diagonals."""
        return [(r, c) for r, c in ((row - 1, column), (row + 1, column),
                                   (row, column - 1), (row, column + 1))
                if 0 <= r < SIZE and 0 <= c < SIZE]

    def _near(self, row, column, kind):
        return any(self.grid[r][c] == kind for r, c in self.neighbors(row, column))

    def pollution(self):
        """One -2 penalty per home next to a mine, capped at -4 colony-wide."""
        homes = sum(self.grid[r][c] == "home" and any(self.grid[a][b] == "mine" and not self.paused[a][b]
                    for a,b in self.neighbors(r,c))
                    for r in range(SIZE) for c in range(SIZE))
        return min(4, 2 * homes)

    def placement_info(self, row, column, kind):
        self._check_tile(row, column)
        if self.paused[row][column]:
            return 'Paused: no power or output. No crew action; timers continue.'
        if kind == "farm":
            return "Farm/home link: +2 Food when powered." if self._near(row, column, "home") else "No home next door: farm has no adjacency bonus."
        if kind == "home":
            farms = sum(self.grid[r][c] == "farm" for r, c in self.neighbors(row, column))
            noise = "Mine noise: -2 Happiness/day." if any(self.grid[r][c] == 'mine' and not self.paused[r][c]
                        for r,c in self.neighbors(row,column)) else "No mine noise."
            return f"Home neighbours: {farms} farm(s). {noise}"
        if kind == "mine":
            return "Mine next to homes: daily noise penalty (colony cap -4)." if self._near(row, column, "home") else "No homes next door: no mine noise."
        return "Plan homes next to farms and away from mines."

    def effects_summary(self):
        labels = {"solar_storm": "Solar 50%", "ore_rush": "Mine bonus +4 Materials",
                  "cold_snap": "Farms 75%", "dust_cloud": "Solar 50% (dust)", "filter_load": "Farm/Mine power +1"}
        if self.ruleset in ('v31', 'v32', 'v33') and self.event_days[self.event_order.index('deposit')] >= 9:
            labels['ore_rush'] = 'Mine bonus +8 Materials'
        return self.time_text("; ".join(f"{labels[name]}: {days} day(s)" for name, days in sorted(self.effects.items())) or "None")

    def _record(self, message):
        self.log.append(self.time_text(message))
        self.log = self.log[-80:]

    def _require_active(self):
        if self.status != "active":
            raise RuleError("This expedition has ended. Start a new colony or load a save.")
        if self.pending_event is not None:
            raise RuleError("Resolve the council event before building or advancing.")

    def build(self, row, column, kind):
        """Validate everything before charging for one construction per day."""
        self._require_active()
        self._check_tile(row, column)
        if not isinstance(kind, str) or kind not in BUILDINGS:
            raise RuleError("Choose one of the four building types.")
        if self.grid[row][column] is not None:
            raise RuleError("That tile is occupied. Select an empty tile.")
        if self.built_today:
            raise RuleError("The crew can build once per day. Advance to the next day.")
        cost = BUILDINGS[kind]["cost"]
        if self.materials < cost:
            raise RuleError(f"Need {cost} Materials; only {self.materials} available.")
        self.materials -= cost
        self.grid[row][column] = kind
        self.levels[row][column] = 1
        self.built_today = True
        self._record(f"Build: {BUILDINGS[kind]['name']} at ({row + 1}, {column + 1}); -{cost} Materials.")
        if self.ruleset in ("v31", "v32", "v33") and kind == "home" and self.counts()["home"] == 1:
            self._record("A window lights up. Tonight, someone can leave the folding beds in HQ.")
        if self.ruleset in ('v32', 'v33') and kind == 'home' and self.memories['home_week'] is None:
            self.memories['home_week'] = self.day

    def _check_tile(self, row, column):
        if type(row) is not int or type(column) is not int:
            raise RuleError("Tile coordinates must be whole numbers.")
        if not (0 <= row < SIZE and 0 <= column < SIZE):
            raise RuleError("Choose a tile inside the map.")

    def upgrade_error(self, row, column):
        """Use the same rejection checks for the UI and the actual upgrade."""
        try:
            self._require_active()
            self._check_tile(row, column)
        except RuleError as exc:
            return str(exc)
        kind = self.grid[row][column]
        if kind not in BUILDINGS:
            return "Select an existing facility. HQ cannot be upgraded."
        if self.levels[row][column] == 2:
            return "This facility is already at maximum level (L2)."
        if self.built_today:
            return "Construction used: building and upgrading share one daily action."
        cost = UPGRADE_COSTS[kind]
        if self.materials < cost:
            return f"Need {cost} Materials; only {self.materials} available."
        return None

    def upgrade(self, row, column):
        error = self.upgrade_error(row, column)
        if error:
            raise RuleError(error)
        kind = self.grid[row][column]
        cost = UPGRADE_COSTS[kind]
        self.materials -= cost
        self.levels[row][column] = 2
        self.built_today = True
        self._record(f"Upgrade: {BUILDINGS[kind]['name']} at ({row + 1}, {column + 1}) "
                     f"to L2; -{cost} Materials; {facility_effect(kind, 2, self.campaign_days)}.")

    def _production(self):
        """Shared by preview and settlement, so the forecast uses the real rules."""
        solar = sum(OUTPUTS["solar"][self.levels[r][c]][1]
            for r in range(SIZE) for c in range(SIZE) if self.grid[r][c] == "solar")
        solar = solar // 2 if ("solar_storm" in self.effects or "dust_cloud" in self.effects) else solar
        energy = self.energy + 2 + solar
        supported = energy >= 2
        energy = max(0, energy - 2)
        homes = [(r, c) for r in range(SIZE) for c in range(SIZE) if self.grid[r][c] == "home"]
        home_power = min(energy, len(homes))
        energy -= home_power
        production = {"food": 0, "materials": 0, "farms": 0, "mines": 0,
                      "offline_tiles": homes[home_power:], "solar": solar,
                      "home_demand": len(homes), "home_power": home_power,
                      "facility_power": 0, "farm_bonus": 0, "ore_bonus": 0,
                      "farm_loss": 0, "filter_power": 0,
                      "paused_tiles": [(r,c) for r in range(SIZE) for c in range(SIZE) if self.paused[r][c]]}
        # Farms have priority. Within each type use row-major order, skipping
        # unaffordable facilities rather than charging for partial production.
        for kind, resource, counter in (("farm", "food", "farms"), ("mine", "materials", "mines")):
            for r in range(SIZE):
                for c in range(SIZE):
                    if self.grid[r][c] != kind or self.paused[r][c]:
                        continue
                    cost, output = OUTPUTS[kind][self.levels[r][c]]
                    if kind == "farm" and self.campaign_days == 15:
                        output = 8 if self.levels[r][c] == 1 else 12
                    extra = int("filter_load" in self.effects)
                    cost += extra
                    if energy >= cost:
                        energy -= cost
                        production["facility_power"] += cost
                        production["filter_power"] += extra
                        if kind == "farm" and "cold_snap" in self.effects:
                            linked = 2 if self._near(r, c, "home") else 0
                            loss = (output + linked) - (output + linked) * 3 // 4
                            output -= loss
                            production["farm_loss"] += loss
                        production[resource] += output
                        if kind == "farm" and self._near(r, c, "home"):
                            production["food"] += 2
                            production["farm_bonus"] += 2
                        production[counter] += 1
                    else:
                        production["offline_tiles"].append((r, c))
        if production["mines"] and "ore_rush" in self.effects:
            bonus = 8 if self.ruleset in ('v31', 'v32', 'v33') and self.event_days[self.event_order.index('deposit')] >= 9 else 4
            production["materials"] += bonus
            production["ore_bonus"] = bonus
        production.update(energy=min(RESOURCE_LIMIT, energy), supported=supported)
        return production

    def _settlement(self):
        """Calculate a whole day without changing state; forecast and play agree."""
        production = self._production()
        available_food = min(RESOURCE_LIMIT, self.food + production["food"])
        demand = self.food_demand
        shortage = max(0, demand - available_food)
        food = max(0, available_food - demand)
        deaths = min(self.population, (shortage + 1) // 2 + (0 if production["supported"] else 1))
        population = self.population - deaths
        pollution = self.pollution()
        morale = (-10 if shortage else 0) - (3 if production["offline_tiles"] else 0)
        morale -= 2 if population >= self.housing else 0
        morale -= pollution
        if morale == 0 and population > 0:
            morale = 1 if self.campaign_days == 15 or self.happiness < 78 else -1 if self.happiness > 78 else 0
        happiness = max(0, min(100, self.happiness + morale))
        tomorrow = self.day + 1
        growth = False
        if population == 0:
            reason = "No survivors remain."
        elif self.ration_days:
            reason = "Growth paused: emergency rations this settlement."
        elif tomorrow % self.growth_interval:
            check = tomorrow + (self.growth_interval - tomorrow % self.growth_interval)
            reason = f"Next growth check: Day {check}."
        elif deaths:
            reason = "Survival losses prevent growth today."
        elif happiness < 40:
            reason = "Growth paused: Happiness below 40."
        elif population >= self.housing:
            reason = "Growth paused: no spare housing."
        elif production["home_power"] < production["home_demand"]:
            reason = "Growth paused: unpowered housing."
        elif food < population + 4:
            reason = f"Growth paused: need {population + 4} Food after meals."
        else:
            food -= 4
            population += 1
            growth = True
            reason = "New arrival: +1 Population; settlement supplies -4 Food."
        return {**production, "new_food": food, "new_energy": production["energy"],
                "new_materials": min(RESOURCE_LIMIT, self.materials + production["materials"]),
                "new_population": population, "new_happiness": happiness,
                "food_demand": demand, "food_shortfall": shortage, "deaths": deaths,
                "pollution": pollution, "growth": growth, "growth_reason": reason}

    def forecast(self):
        """Include current timed effects, survival, Happiness and growth; exclude new council decisions."""
        report = self._settlement()
        result = dict(report)
        for key in ("food", "energy", "materials", "population", "happiness"):
            result[key] = report[f"new_{key}"] - getattr(self, key)
        result["offline"] = len(report["offline_tiles"])
        return result

    def _report_text(self, report, title):
        text = (f"{title}\n"
                f"Food: +{report['food']} produced (home links +{report['farm_bonus']}); meals -{report['food_demand']}.\n"
                f"Energy: HQ +2, Solar +{report['solar']}; life support -2, homes -{report['home_power']}, facilities -{report['facility_power']}.\n"
                f"Materials: +{report['materials']} produced (ore bonus +{report['ore_bonus']}).\n"
                f"Offline sites: {len(report['offline_tiles'])}; food shortfall: {report['food_shortfall']}; colonists lost: {report['deaths']}.\n"
                f"Happiness: {self.happiness} -> {report['new_happiness']} (mine noise -{report['pollution']}/day).\n"
                f"{report['growth_reason']}\n"
                f"After settlement: Food {report['new_food']}, Energy {report['new_energy']}, Materials {report['new_materials']}, Population {report['new_population']}.\n"
                f"Effects used this day: {self.effects_summary()}")
        if self.ruleset in ("v31", "v32", "v33"):
            text += f"\nWeather loss: {report['farm_loss']} Food; filter power included: {report['filter_power']} Energy."
        if self.ruleset == 'v33':
            text += f"\nPaused by you: {len(report['paused_tiles'])}. No power or output; timers continue."
        return self.time_text(text)

    def planning_report(self):
        if self.status != "active":
            return "Expedition ended. No further settlements."
        report = self._settlement()
        return self._report_text(report, f"NEXT: DAY {self.day + 1} (before a new council choice)")

    def next_day(self):
        """Settle production, survival, growth, then the scheduled council event."""
        self._require_active()
        report = self._settlement()
        if self.ruleset in ('v32', 'v33') and self.ration_days:
            normal = deepcopy(self)
            normal.ration_days = 0
            self.memories['ration_rescues'] += max(0, normal.forecast()['deaths'] - report['deaths'])
        self.last_report = self._report_text(report, f"SETTLED: DAY {self.day + 1}")
        self.day += 1
        self.built_today = False
        for key in ("food", "energy", "materials", "population", "happiness"):
            setattr(self, key, report[f"new_{key}"])
        self._record(f"Day {self.day}: Food +{report['food']} / meals -{report['food_demand']}; "
                     f"Materials +{report['materials']}; Energy reserve {self.energy}; Happiness {self.happiness}.")
        self._record(report["growth_reason"])
        if self.ruleset in ('v31', 'v32', 'v33') and report['growth']:
            self._record("A new resident arrives. Another name belongs beside the door.")
        if report["food_shortfall"] or report["offline_tiles"]:
            self._record(f"Crisis: food shortfall {report['food_shortfall']}; offline {len(report['offline_tiles'])}; deaths {report['deaths']}.")
        for name, remaining in self.effects.items():
            if remaining == 1:
                self._record(f"Effect ended: {EFFECTS[name]['title']}.")
        self.effects = {name: days - 1 for name, days in self.effects.items() if days > 1}
        self.ration_days = 0
        if self.ruleset in ('v32', 'v33') and self.population > 0:
            from polish import BULLETINS
            key = f'week{self.day}'
            if key in BULLETINS and key not in self.bulletins_seen:
                self.bulletins_seen.append(key)
                self._record(BULLETINS[key][0])
            if self.day in (6, 14, 22) and self.beacon_stage < 3:
                self._record('Beacon reminder: a new HQ stage is unlocked. Finish all stages by Week 29.')
        if self.campaign_days == 30 and self.day in (10, 20):
            self._record(f"Milestone: Day {self.day}; {self.population} pioneers still together.")
        self._check_end()
        if self.status == "active" and self.day in self.event_days:
            self.pending_event = self.event_order[self.event_days.index(self.day)]
            if self.ruleset in ("v31", "v32", "v33"):
                self.event_snapshot = {"turn": self.day, "population": self.population,
                                       "options": offer_options(self.pending_event, self.day, self.population, self.ruleset)}
            self._record(f"Council alert: {self.event_view()['title']}.")

    def option_error(self, index):
        """Return why a choice is unavailable, or None when it is affordable."""
        if self.status != "active" or self.pending_event is None:
            return "There is no council decision waiting."
        if type(index) is not int or index not in (0, 1):
            return "Choose option 1 or 2."
        option = self.event_options()[index]
        for resource, cost in option.get("cost", {}).items():
            if getattr(self, resource) < cost:
                return f"Need {cost} {resource.title()}."
        new_population = self.population + option.get("change", {}).get("population", 0)
        if new_population > self.housing:
            return f"Need housing for {new_population} people; capacity is {self.housing}."
        return None

    def choose_event(self, index):
        """Costs require full payment; advertised 'up to' losses stop at zero."""
        error = self.option_error(index)
        if error:
            raise RuleError(error)
        event = EVENTS[self.pending_event]
        option = self.event_options()[index]
        before = {key: getattr(self, key) for key in ("food", "energy", "materials", "population", "happiness")}
        for resource, cost in option.get("cost", {}).items():
            setattr(self, resource, getattr(self, resource) - cost)
        for resource, change in option.get("change", {}).items():
            limit = 100 if resource == "happiness" else RESOURCE_LIMIT
            setattr(self, resource, max(0, min(limit, getattr(self, resource) + change)))
        for name, days in option.get("effects", {}).items():
            self.effects[name] = days
        if self.ruleset in ('v32', 'v33') and self.pending_event == 'immigrants' and index == 0:
            self.memories['welcomed'] += max(0, self.population - before['population'])
        changes = ", ".join(f"{key.title()} {getattr(self, key) - value:+d}"
                            for key, value in before.items() if getattr(self, key) != value)
        consequence = f"Council: {option['label']}. {changes or 'No immediate resource change'}."
        if option.get("effects"):
            consequence += f" Active effects: {self.effects_summary()}."
        self._record(consequence)
        if self.ruleset in ("v31", "v32", "v33"):
            from narrative import REACTIONS
            self._record(REACTIONS[self.pending_event][index][0])
        self.last_report += "\n" + self.time_text(consequence)
        self.pending_event = None
        self.event_snapshot = None
        self._check_end()

    def _check_end(self):
        if self.population == 0:
            self.status = "lost"
            self.reason = "No colonists remain. The beacon falls silent."
        elif self.day == self.campaign_days and self.campaign_days == 30 and self.beacon_stage < 3:
            self.status = "lost"
            self.reason = "Day 30: the supply ship passed without a completed beacon. The colony is stranded."
        elif self.day == self.campaign_days:
            self.status = "won"
            self.reason = ("The supply ship has arrived. Your colony survived fifteen days."
                           if self.campaign_days == 15 else "Day 30: your beacon guides the supply ship home. The colony is saved.")

    def result(self):
        buildings = sum(self.counts().values())
        score = (15 * self.population + 5 * buildings + min(100, self.food)
                 + min(100, self.energy) // 2 + min(100, self.materials) // 2
                 + 3 * self.upgrade_count + self.happiness // 5)
        if self.status == "lost":
            title = "Silent Beacon" if self.population == 0 else "Stranded Colony"
        elif self.population >= (10 if self.campaign_days == 15 else 13) and score >= (300 if self.campaign_days == 15 else 390) and self.happiness >= (65 if self.campaign_days == 15 else 80):
            title = "New Eden"
        elif self.population >= (7 if self.campaign_days == 15 else 11 if self.ruleset in ('v32', 'v33') else 9) and score >= (220 if self.campaign_days == 15 else 300) and self.happiness >= (40 if self.campaign_days == 15 else 65 if self.ruleset in ('v32', 'v33') else 45):
            title = "Prosperous Colony"
        else:
            title = "Struggling Outpost"
        return title, score

    def summary(self):
        counts = self.counts()
        if self.status == "lost" and self.population == 0:
            if self.ruleset in ('v32', 'v33'):
                return f'After {self.day} weeks, the landing site is silent. No one answers the final signal.'
            return (f"After {self.day} days, the landing site is silent. "
                    "Its empty homes are a reminder: expansion needs a food supply.")
        if self.status == "lost":
            return "The survivors built a home, but missed their only rescue window. Finish all three HQ stages next time."
        mood = "a hopeful community" if self.happiness >= 65 else "a cautious community" if self.happiness >= 40 else "a weary community"
        return (f"{self.population} pioneers now call this world home: {mood}. "
                f"Your {sum(counts.values())} facilities include {self.upgrade_count} L2 upgrades. "
                f"The supply ship finds {self.food} Food and {self.materials} Materials in reserve.")

    def memory_summary(self):
        if self.ruleset not in ('v32', 'v33'):
            return 'Legacy expedition: no new historical memories are invented.'
        lines=[]
        if self.memories['home_week'] is not None:
            lines.append(f"Life record: the first home lit up in Week {self.memories['home_week']}.")
        if self.memories['beacon_week'] is not None:
            lines.append(f"Engineering record: beacon completed in Week {self.memories['beacon_week']}.")
        lines.append(f"Life record: {self.memories['welcomed']} surveyors welcomed; {self.memories['ration_rescues']} survival losses avoided by rationing.")
        lines.append('New Eden: Population 13+, Happiness 80+, Score 390+.')
        lines.append('Prosperous Colony: Population 11+, Happiness 65+, Score 300+.')
        return '\n'.join(lines)
