from rich.console import Console
import time


console = Console(record=True)
try:    
    import _PyStats
except ImportError:
    console.print('[red] PyStats is not installed. Please install it with')#One day I will make it work with pip3.
    exit()
# Changed it to pystat_print because it wouldn't let me print other things that I wanted using
# the standard print statement
pystat_print = console.print

if __name__ == "__main__":
    info = _PyStats.VisualWrapper(_PyStats.working_path)
    if info.img_render(remove_check=False, force_show=True, clear_screen=True)[0]: #has a built in if statement checker so no need to re define also i wanted it to be my default render mode so i made it this way
        quit(  )
    
    if _PyStats.args.adhd:
        info = _PyStats.VisualWrapper(_PyStats.working_path)
    else:

        pystat_print(info.get_all(True))
        
