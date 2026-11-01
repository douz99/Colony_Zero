"""Optional original WAV cues; unsupported devices/platforms stay silent."""
from pathlib import Path

CUES=('build','event','warning','beacon','settle','choice','ration','victory','failure')

try:
    import winsound
except ImportError:
    winsound = None


class SoundPlayer:
    def __init__(self):
        self.folder = Path(__file__).resolve().parent / 'assets'
        self.available = winsound is not None and all((self.folder / (name + '.wav')).is_file()
                                                       for name in CUES)
        # Quiet startup suits classroom demos; the player opts in explicitly.
        self.enabled = False

    def play(self, name):
        if not self.enabled or not self.available or name not in CUES:
            return False
        try:
            winsound.PlaySound(str(self.folder / (name + '.wav')),
                               winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        except (OSError, RuntimeError):
            self.available = False
            self.enabled = False
            return False
        return True

    def stop(self):
        if self.enabled and winsound is not None:
            try:
                winsound.PlaySound(None, 0)
            except (OSError, RuntimeError):
                pass
