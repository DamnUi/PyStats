# PyStats

Project in semi-beta 

Things to do currently:
Add a dashboard to view all info in
Possible to make the dashboard in flask?

Currently, `import_count` function is not working and `variable_count` is kind of messed up also  





pystat is the venv
## Textual TUI (new!)

A full terminal-app version of PyStats built with [Textual](https://github.com/textualize/textual) -
keyboard navigation, tabs, tables, tree view, and keyboard shortcuts.

### Run it

```bash
pip install textual
python Src_Stat/PyStatsTUI.py -df Src_Stat
# or, from inside Src_Stat:
python -m pystats_tui -df Src_Stat
```

### Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit |
| `r` | Reload statistics |
| `s` | Save screen as SVG |
| `?` | Help |
| `tab` | Switch tabs / focus |

The classic Rich dashboard (PyStats.py) still works exactly as before - the
TUI is an addition, not a replacement.
