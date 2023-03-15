from rich.console import Console
import inspect
from pathlib import Path
import os


console = Console(record=True)
try:    
    import _PyStats
except ImportError:
    console.print('[red] PyStats is not installed. Please install it with')#One day I will make it work with pip3.
    exit()
# Changed it to pystat_print because it wouldn|'t let me print other things that I wanted using
# the standard print statement
pystat_print = console.print


def main():
    info = _PyStats.VisualWrapper(_PyStats.working_path)
    if info.img_render(remove_check=True, force_show=False, clear_screen=False)[0]: #has a built in if statement checker so no need to re define also i wanted it to be my default render mode so i made it this way
        quit()
    
    if _PyStats.args.adhd:
        info = _PyStats.VisualWrapper(_PyStats.working_path)
    else:
        pystat_print(info.get_all(True))

main()

        
