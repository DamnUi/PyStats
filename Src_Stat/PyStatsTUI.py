"""PyStats TUI launcher.

A Textual-based terminal UI for PyStats. Run directly:

    python PyStatsTUI.py [-df <path>] [--vars N] [--adhd]

or as a module from inside Src_Stat:

    python -m pystats_tui

Requires: textual (pip install textual). The classic Rich dashboard is still
available via PyStats.py / _PyStats.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pystats_tui.app import main

if __name__ == "__main__":
    main()
