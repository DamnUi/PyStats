from rich.console import Console

import _PyStats

console = Console(record=True)
# Changed it to pystat_print because it wouldn't let me print other things that I wanted using
# the standard print statement
pystat_print = console.print

if __name__ == "__main__":
    info = _PyStats.VisualWrapper(_PyStats.working_path)
    if _PyStats.args.adhd:
        info = _PyStats.VisualWrapper(_PyStats.working_path)

    if _PyStats.args.imgpath:
        info.img_render(remove_check=False, force_show=True, clear_screen=True)
    else:
        pystat_print(info.get_all())
