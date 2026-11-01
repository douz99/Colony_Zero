"""Versioned JSON saves, strict validation and atomic replacement."""

import json
import os
from pathlib import Path
import tempfile
import time

from engine import BEACON_STAGES, BUILDINGS, Game, LEGACY_EVENTS, V30_EVENTS, RESOURCE_LIMIT, SIZE, empty_memories
from events import EFFECTS, EVENTS, offer_options

SAVE_VERSION = 7
MAX_SAVE_BYTES = 100_000
LEGACY_FIELDS = {"version", "grid", "food", "energy", "materials", "population", "day",
          "built_today", "status", "reason", "pending_event", "event_order", "log"}
V2_FIELDS = LEGACY_FIELDS | {"levels", "happiness"}
V3_FIELDS = V2_FIELDS | {"effects", "last_report"}
V4_FIELDS = V3_FIELDS | {"campaign_days", "beacon_stage", "ration_uses", "ration_days"}
V5_FIELDS = V4_FIELDS | {"ruleset", "event_snapshot"}
V6_FIELDS = V5_FIELDS | {"story_seed", "memories", "bulletins_seen"}
FIELDS = V6_FIELDS | {"paused"}


class SaveError(ValueError):
    """An unreadable, unsupported or inconsistent save file."""


def to_data(game):
    data = {name: getattr(game, name) for name in FIELDS if name != "version"}
    data["version"] = SAVE_VERSION
    return data


def from_data(data):
    """Validate untrusted JSON completely before replacing the current game."""
    def require(condition, message):
        if not condition:
            raise SaveError(message)

    def integer(value, low, high):
        # bool is an int subclass, but true is not a meaningful resource value.
        return type(value) is int and low <= value <= high

    require(isinstance(data, dict), "Save must be a JSON object.")
    version = data.get("version")
    require(type(version) is int and version in (1, 2, 3, 4, 5, 6, SAVE_VERSION),
            "Unsupported save version; V3.3 reads versions 1 through 7.")
    expected = {1: LEGACY_FIELDS, 2: V2_FIELDS, 3: V3_FIELDS, 4: V4_FIELDS, 5: V5_FIELDS, 6: V6_FIELDS, 7: FIELDS}[version]
    require(set(data) == expected,
            "Missing or unexpected save fields.")
    grid = data["grid"]
    require(isinstance(grid, list) and len(grid) == SIZE, "Map must have five rows.")
    for row in grid:
        require(isinstance(row, list) and len(row) == SIZE, "Map rows must have five tiles.")
        require(all(tile is None or (isinstance(tile, str) and tile in {*BUILDINGS, "hq"})
                    for tile in row), "Unknown map tile.")
    require(grid[2][2] == "hq" and sum(row.count("hq") for row in grid) == 1,
            "Exactly one HQ must occupy the central tile.")
    # Migrate only after the original map has passed validation.
    data = json.loads(json.dumps(data))
    if version == 1:
        data["levels"] = [[1 if tile in BUILDINGS else 0 for tile in row] for row in grid]
        data["happiness"] = 70
    if version < 3:
        data["effects"] = {}
        data["last_report"] = "Imported older save: no V2.0 daily report or timed effects were recorded."
    if version < 4:
        # Original campaign dates/deck/endings remain meaningful after import.
        data.update(campaign_days=15, beacon_stage=0, ration_uses=0, ration_days=0)
    require(integer(data["campaign_days"], 15, 30) and data["campaign_days"] in (15, 30),
            "Invalid campaign length.")
    if version < 5:
        data.update(ruleset="v20" if data["campaign_days"] == 15 else "v30", event_snapshot=None)
    if version < 6:
        data.update(story_seed=0, memories=empty_memories(), bulletins_seen=[])
    if version < 7:
        data['paused'] = [[False for _ in range(SIZE)] for _ in range(SIZE)]
        require(data['ruleset'] != 'v33', 'Older format cannot contain V3.3 rules.')
    paused = data['paused']
    require(isinstance(paused,list) and len(paused) == SIZE, 'Invalid production switches.')
    for r,row in enumerate(paused):
        require(isinstance(row,list) and len(row) == SIZE, 'Invalid production switches.')
        for c,value in enumerate(row):
            require(type(value) is bool and (not value or data['ruleset'] == 'v33' and grid[r][c] in ('farm','mine')),
                    'Switch does not match a controllable facility.')
    require(isinstance(data["ruleset"], str) and data["ruleset"] in ("v20", "v30", "v31", "v32", "v33")
            and (data["ruleset"] == "v20") == (data["campaign_days"] == 15), "Invalid campaign ruleset.")
    require(integer(data["beacon_stage"], 0, 3), "Invalid beacon stage.")
    require(integer(data["ration_uses"], 0, 2) and integer(data["ration_days"], 0, 1),
            "Invalid emergency ration counters.")
    require(data["ration_days"] <= data["ration_uses"], "Ration order has no recorded use.")
    require(data["campaign_days"] != 15 or data["beacon_stage"] == 0,
            "Legacy campaign cannot contain beacon work.")
    data["version"] = SAVE_VERSION
    require(isinstance(data["last_report"], str) and len(data["last_report"]) <= 2500,
            "Invalid daily report.")
    require(isinstance(data["effects"], dict) and set(data["effects"]) <= set(EFFECTS),
            "Unknown timed effects.")
    for name, days in data["effects"].items():
        require(integer(days, 1, EFFECTS[name]["duration"]), "Invalid effect duration.")
    require(integer(data["happiness"], 0, 100), "Happiness must be a whole number from 0 to 100.")
    levels = data["levels"]
    require(isinstance(levels, list) and len(levels) == SIZE, "Levels must have five rows.")
    for r, row in enumerate(levels):
        require(isinstance(row, list) and len(row) == SIZE, "Level rows must have five tiles.")
        for c, level in enumerate(row):
            require(integer(level, 0, 2), "Invalid facility level.")
            require(level in (1, 2) if grid[r][c] in BUILDINGS else level == 0,
                    "Facility levels do not match map tiles.")
    for key in ("food", "energy", "materials"):
        require(integer(data[key], 0, RESOURCE_LIMIT), f"Invalid {key} value.")
    require(integer(data["population"], 0, 102 if version == 1 else 150), "Invalid population.")
    require(integer(data["day"], 0, data["campaign_days"]), "Invalid day.")
    require(data["ration_uses"] <= data["day"] + data["ration_days"], "Too many ration orders for this day.")
    require(type(data["built_today"]) is bool, "Invalid construction flag.")
    require(isinstance(data["status"], str) and data["status"] in ("active", "won", "lost"),
            "Invalid expedition status.")
    require(isinstance(data["reason"], str) and len(data["reason"]) <= 200, "Invalid result message.")
    order = data["event_order"]
    deck = set(LEGACY_EVENTS) if data["campaign_days"] == 15 else set(V30_EVENTS) if data["ruleset"] == "v30" else set(EVENTS)
    require(isinstance(order, list) and len(order) == len(deck)
            and all(isinstance(item, str) for item in order) and set(order) == deck,
            "Event deck must contain every campaign event exactly once.")
    pending = data["pending_event"]
    require(pending is None or (isinstance(pending, str) and pending in EVENTS), "Unknown pending event.")
    require(isinstance(data["log"], list) and 1 <= len(data["log"]) <= 80
            and all(isinstance(line, str) and len(line) <= 500 for line in data["log"]),
            "Invalid colony log.")
    game = Game(seed=0, campaign_days=data["campaign_days"], ruleset=data["ruleset"])
    # Copy containers so callers cannot mutate a loaded game through input data.
    clean = json.loads(json.dumps(data))
    for name in FIELDS - {"version"}:
        setattr(game, name, clean[name])
    require(integer(game.story_seed, 0, 2**31-1), "Invalid story seed.")
    require(isinstance(game.memories, dict) and set(game.memories) == set(empty_memories()), "Invalid colony memories.")
    for key in ('home_week', 'beacon_week'):
        require(game.memories[key] is None or integer(game.memories[key], 0, min(game.day,29)), "Invalid memory date.")
    require(integer(game.memories['welcomed'],0,2) and game.memories['welcomed'] in (0,2)
            and integer(game.memories['ration_rescues'],0,150), "Invalid memory counters.")
    require(isinstance(game.bulletins_seen,list) and all(isinstance(item,str) for item in game.bulletins_seen)
            and len(set(game.bulletins_seen)) == len(game.bulletins_seen), "Invalid bulletin history.")
    if game.ruleset in ('v32', 'v33'):
        from polish import BULLETINS
        require(set(game.bulletins_seen) <= {key for key in BULLETINS if int(key[4:]) <= game.day}, "Bulletin is from a future week.")
        require((game.memories['home_week'] is not None) == bool(game.counts()['home']), "Home memory does not match the map.")
        require((game.memories['beacon_week'] is not None) == (game.beacon_stage == 3), "Beacon memory does not match progress.")
        require(game.memories['beacon_week'] is None or game.memories['beacon_week'] >= 22, "Beacon memory predates unlock.")
        require(game.memories['ration_rescues'] == 0 or game.ration_uses > 0, "Ration memory has no order.")
        if game.memories['welcomed']:
            require(game.day >= game.event_days[order.index('immigrants')] and pending != 'immigrants', "Immigration memory predates the choice.")
    else:
        require(game.story_seed == 0 and game.memories == empty_memories() and game.bulletins_seen == [], "Legacy memories must remain empty.")
    if game.ruleset in ("v31", "v32", "v33"):
        require(set(order[:2]) <= set(V30_EVENTS) and set(order[i] for i in (2, 5, 8)) == {"cold", "dust", "filters"}
                and order[11] == "community" and ("storm" in order[:2] or order[3] == "storm"),
                "Event deck violates opening or recovery spacing.")
    else:
        require(set(game.effects) <= {"solar_storm", "ore_rush"}, "Legacy campaign has new effects.")
    if game.ruleset in ("v31", "v32", "v33") and pending is not None:
        expected_offer = {"turn": game.day, "population": game.population,
                          "options": offer_options(pending, game.day, game.population, game.ruleset)}
        require(json.dumps(game.event_snapshot, sort_keys=True) == json.dumps(expected_offer, sort_keys=True),
                "Invalid locked council offer.")
    else:
        require(game.event_snapshot is None, "Unexpected council offer.")
    game.imported_from_v1 = version == 1
    game.imported_from_version = version if version < SAVE_VERSION else None
    buildings = sum(game.counts().values())
    require(game.population <= game.housing, "Population exceeds housing capacity.")
    require(buildings + game.upgrade_count + game.beacon_stage <= game.day + int(game.built_today),
            "Too many construction actions for this day.")
    require(not game.built_today or buildings + game.beacon_stage > 0, "Construction flag needs a building.")
    if game.beacon_stage:
        require(game.day >= BEACON_STAGES[game.beacon_stage - 1][0], "Beacon stage is not unlocked yet.")
    if game.status == "active":
        require(game.population > 0 and game.day < game.campaign_days and game.reason == "",
                "Active game has inconsistent survival or day values.")
    elif game.status == "won":
        require(game.population > 0 and game.day == game.campaign_days and bool(game.reason)
                and (game.campaign_days == 15 or game.beacon_stage == 3),
                "Victory requires the campaign deadline, survivors and the required beacon.")
    else:
        require((game.population == 0 or (game.campaign_days == 30 and game.day == 30 and game.beacon_stage < 3))
                and game.day > 0 and bool(game.reason), "Failure requires no survivors or a missed beacon deadline.")
    require(game.status == "active" or not game.built_today,
            "An ended expedition cannot have a pending construction action.")
    require(game.status == "active" or game.ration_days == 0,
            "An ended expedition cannot have active emergency rations.")
    require(pending is None or game.ration_days == 0, "Rations must settle before a council event.")
    if pending is not None:
        require(game.status == "active" and game.day in game.event_days and not game.built_today,
                "Pending event is inconsistent with this turn.")
        require(pending == order[game.event_days.index(game.day)], "Pending event does not match the deck.")
    for name, remaining in game.effects.items():
        source = EFFECTS[name]["event"]
        start_day = game.event_days[order.index(source)]
        elapsed = game.day - start_day
        require(0 <= elapsed < EFFECTS[name]["duration"] and pending != source
                and remaining == EFFECTS[name]["duration"] - elapsed,
                "Timed effect is inconsistent with the event date.")
    return game


def save_game(game, filename):
    """Write beside the target, then replace it; failed writes preserve old saves."""
    target = Path(filename)
    temporary = None
    try:
        data = to_data(game)
        from_data(data)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent,
                                         prefix=".colony-", suffix=".tmp", delete=False) as stream:
            temporary = stream.name
            json.dump(data, stream, indent=2, ensure_ascii=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # Desktop scanners/editors may briefly hold an existing save on Windows.
        # Retry only a denied atomic replacement; never delete the old save first.
        for attempt in range(3):
            try:
                os.replace(temporary, target)
                break
            except PermissionError:
                if attempt == 2:
                    raise
                time.sleep(0.05 * (attempt + 1))
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        raise SaveError(f"Could not save colony: {exc}") from exc
    finally:
        if temporary is not None:
            try:
                Path(temporary).unlink(missing_ok=True)
            except OSError:
                pass


def load_game(filename):
    try:
        with Path(filename).open("r", encoding="utf-8") as stream:
            content = stream.read(MAX_SAVE_BYTES + 1)
        if len(content.encode("utf-8")) > MAX_SAVE_BYTES:
            raise SaveError("Save is too large (maximum 100 KB).")
        return from_data(json.loads(content))
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        raise SaveError(f"Could not load colony: {exc}") from exc
