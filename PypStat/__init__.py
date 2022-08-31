from ast import main
from rich.console import Console

def Main():
    console = Console(record=True)
    try:    
        import PypStat._PyStats as _PyStats
    except ImportError:
        import _PyStats
    # Changed it to pystat_print because it wouldn't let me print other things that I wanted using
    # the standard print statement
    pystat_print = console.print

    info = _PyStats.VisualWrapper(_PyStats.working_path)
    if info.img_render(remove_check=False, force_show=True, clear_screen=True)[0]: #has a built in if statement checker so no need to re define also i wanted it to be my default render mode so i made it this way
        quit()
    
    if _PyStats.args.adhd:
        info = _PyStats.VisualWrapper(_PyStats.working_path)
    else:

        pystat_print(info.get_all())



Main()