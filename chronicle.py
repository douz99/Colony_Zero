"""Read factual narrative from the existing bounded log; no simulation state."""
import re
from narrative import REACTIONS
from polish import BULLETINS


def entries(game):
    """Keep multiple stories in order. Unknown old dates stay unlabelled."""
    stories = {pair[0] for options in REACTIONS.values() for pair in options}
    stories.update(pair[0] for pair in BULLETINS.values())
    stories.update({
        'A window lights up. Tonight, someone can leave the folding beds in HQ.',
        'A new resident arrives. Another name belongs beside the door.',
        'The first test leaves a clear line in the noise.',
        "Someone pins the ship's approach time beside the radio.",
        'Three green lights. At last, this place has a voice.',
        'Four pioneers step into the dust. Thirty weeks to light a way home.',
    })
    # Beacon prose is already recorded immediately after its dated resource fact.
    beacon_prefixes = ('The first test', 'A steady pulse', 'The signal', 'For a moment')
    result=[]
    week=None
    for message in game.log:
        match=re.match(r'(?:Day|Week) (\d+):',message)
        if match:week=int(match[1])
        if message.startswith('Four pioneers step into the dust.'):
            week=0
        if message in stories or message.startswith(beacon_prefixes):
            if message.startswith('A window lights up.'):
                week=game.memories.get('home_week',week)
            result.append((week,message))
    if game.status != 'active':
        result.append((game.day,game.reason))
    return result


def latest(game):
    records=entries(game)
    return records[-1] if records else (None,'Open Report for the full settlement calculation.')
