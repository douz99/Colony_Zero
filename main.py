# RUN THIS FILE: python main.py
"""Desktop entry point. The game uses only the Python standard library."""

import sys


def main():
    try:
        import tkinter as tk
        from gui import ColonyApp
    except ImportError as exc:
        print(f"Colony Zero needs a desktop Python installation with Tkinter.\n{exc}")
        print("See README.md for the desktop Python setup.")
        return 1
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(f"Cannot open a desktop window: {exc}")
        print("Use a local desktop with Tk/Tcl installed. See README.md.")
        return 1
    ColonyApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
