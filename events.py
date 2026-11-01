"""Encounters, published scaling and bounded temporary consequences."""

from copy import deepcopy

EFFECTS = {
    "cold_snap": {"title": "Cold front", "duration": 2, "description": "Farm output 75% for next 2 weeks (round down per farm)", "event": "cold"},
    "dust_cloud": {"title": "Dust season", "duration": 3, "description": "Solar output 50% for next 3 weeks (does not stack with storms)", "event": "dust"},
    "filter_load": {"title": "Filter bypass", "duration": 3, "description": "each powered Farm/Mine needs +1 Energy for next 3 weeks", "event": "filters"},
    "solar_storm": {"title": "Solar storm", "duration": 2,
                    "description": "solar generation halved for next 2 days (round down)", "event": "storm"},
    "ore_rush": {"title": "Rover extraction", "duration": 3,
                 "description": "+4 Materials/day for next 3 days if any mine is powered", "event": "deposit"},
}

EVENTS = {
    "cold": {
        "title": "The long blue frost", "story": "A cold front is approaching the landing site.",
        "options": (
            {"label": "Keep the heaters running", "cost": {"energy": 8}, "change": {"happiness": 2}},
            {"label": "Protect the roots; rest the outer beds", "change": {"happiness": -2}, "effects": {"cold_snap": 2}},
        ),
    },
    "dust": {
        "title": "A sky without sunrise", "story": "Fine dust is settling on the arrays.",
        "options": (
            {"label": "Fit protective array screens", "cost": {"materials": 12}, "change": {"happiness": 1}},
            {"label": "Wait for clearer skies", "change": {"happiness": -2}, "effects": {"dust_cloud": 3}},
        ),
    },
    "filters": {
        "title": "What we breathe", "story": "The production filters need attention.",
        "options": (
            {"label": "Replace the filter mesh", "cost": {"materials": 10, "energy": 4}, "change": {"happiness": 3}},
            {"label": "Run the backup filter cycle", "change": {"happiness": -2}, "effects": {"filter_load": 3}},
        ),
    },
    "community": {
        "title": "One table for everyone", "story": "Residents are preparing a shared supply pack.",
        "options": (
            {"label": "Set aside a full community supply", "cost": {"food": 12, "energy": 4}, "change": {"happiness": 8}},
            {"label": "Share a smaller reserve pack", "change": {"food": -4, "happiness": -6}},
        ),
    },
    "storm": {
        "title": "The sky turns electric",
        "story": "A two-day solar storm is coming. Spend building materials on shielding, or rely on stored energy while solar output falls?",
        "options": (
            {"label": "Shield the solar arrays", "cost": {"materials": 8}, "change": {"happiness": 2}},
            {"label": "Ride out the storm", "change": {"happiness": -3}, "effects": {"solar_storm": 2}},
        ),
    },
    "immigrants": {
        "title": "A knock from orbit",
        "story": "Two surveyors request a permanent home. They need space and arrival supplies. Their shuttle carries spare parts.",
        "options": (
            {"label": "Welcome the surveyors", "cost": {"food": 4}, "change": {"population": 2, "happiness": 5}},
            {"label": "Exchange a farewell signal", "change": {"energy": -2, "materials": 3, "happiness": -2}},
        ),
    },
    "fault": {
        "title": "The midnight rattle",
        "story": "A storage converter is vibrating. Replace its worn casing, or drain it and recover reusable parts?",
        "options": (
            {"label": "Repair the converter", "cost": {"materials": 5}, "change": {"energy": 2, "happiness": 2}},
            {"label": "Drain and salvage", "change": {"energy": -5, "materials": 3, "happiness": -3}},
        ),
    },
    "contamination": {
        "title": "Something in the pantry",
        "story": "A sealed food batch contains alien spores. Sterilise it with heat, or discard the suspect supplies?",
        "options": (
            {"label": "Heat-sterilise the batch", "cost": {"energy": 4}, "change": {"happiness": 2}},
            {"label": "Discard suspect food", "change": {"food": -8, "happiness": -4}},
        ),
    },
    "deposit": {
        "title": "Silver under the dust",
        "story": "A rover finds an ore pocket. Invest in three days of extraction, or collect surface fragments now? Late investments may not pay back before the ship arrives.",
        "options": (
            {"label": "Fund rover extraction", "cost": {"energy": 4, "materials": 3}, "change": {"happiness": 2}, "effects": {"ore_rush": 3}},
            {"label": "Collect surface fragments", "change": {"materials": 5, "happiness": 1}},
        ),
    },
    "protest": {
        "title": "An empty seat at dinner",
        "story": "One pioneer wants to leave. Share a special meal to persuade them, or return their ration and wish them well?",
        "options": (
            {"label": "Host a colony dinner", "cost": {"food": 6}, "change": {"happiness": 10}},
            {"label": "Accept the departure", "change": {"population": -1, "food": 2, "happiness": -8}},
        ),
    },
    "medical": {
        "title": "A fever in the habitat",
        "story": "The crew is exhausted by an unfamiliar fever. Power the medical heater, or use food reserves for a slower recovery?",
        "options": (
            {"label": "Power the medical heater", "cost": {"energy": 6, "materials": 4}, "change": {"happiness": 6}},
            {"label": "Rest and use recovery rations", "change": {"food": -6, "happiness": -4}},
        ),
    },
    "festival": {
        "title": "A small light in the dark",
        "story": "The residents want a lantern night to celebrate their new home. Spend supplies on a shared memory, or keep the workshop running for spare parts?",
        "options": (
            {"label": "Hold the lantern night", "cost": {"food": 10, "energy": 4}, "change": {"happiness": 12}},
            {"label": "Work the extra shift", "change": {"materials": 5, "happiness": -4}},
        ),
    },
}


def offer_options(event_id, turn, population, ruleset='v31'):
    """Week9+: costs use population, never hidden stock or win-rate penalties.

    One population unit is charged per listed weight; late phase (week21+)
    adds3 to each up-front cost. The result is locked when the event arrives.
    """
    options = deepcopy(EVENTS[event_id]["options"])
    if turn < 9:
        return list(options)
    if event_id == "deposit":
        options[0]["ore_bonus"] = 8
    weights = {
        "storm": {"materials": 2}, "immigrants": {"food": 2},
        "fault": {"materials": 2}, "contamination": {"energy": 2},
        "deposit": {"energy": 1, "materials": 1}, "protest": {"food": 2},
        "medical": {"energy": 1, "materials": 1}, "festival": {"food": 2, "energy": 1},
        "cold": {"energy": 2}, "dust": {"materials": 2},
        "filters": {"materials": 1, "energy": 1}, "community": {"food": 3, "energy": 1},
    }
    for resource, weight in weights[event_id].items():
        options[0]["cost"][resource] += weight * population + (3 if turn >= 21 else 0)
    losses = {"fault": ("energy", 2), "contamination": ("food", 3), "community": ("food", 1)}
    if event_id in losses:
        resource, weight = losses[event_id]
        options[1]["change"][resource] -= population * weight
    if ruleset in ('v32', 'v33'):
        if event_id == 'immigrants':
            options[0]['cost']['food'] -= population
            options[0]['change']['materials'] = 6
        elif event_id == 'fault':
            options[0]['cost']['materials'] -= population
            options[0]['change']['energy'] = 4
        elif event_id == 'community':
            options[0]['cost']['food'] -= population
            options[0]['change']['happiness'] = 12
    return list(options)


def describe_option(option):
    """Build UI text from the effect data to keep labels and rules consistent."""
    parts = []
    for resource, cost in option.get("cost", {}).items():
        parts.append(f"pay {cost} {resource.title()}")
    for resource, change in option.get("change", {}).items():
        if change < 0 and resource not in ("population", "happiness"):
            parts.append(f"lose up to {-change} {resource.title()}")
        else:
            parts.append(f"{resource.title()} {change:+d}")
    for name in option.get("effects", {}):
        parts.append("+8 Materials/week for next 3 weeks if any mine is powered" if name == "ore_rush" and option.get("ore_bonus") == 8 else EFFECTS[name]["description"])
    return "; ".join(parts) or "No resource change"
