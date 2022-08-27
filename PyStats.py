import argparse
import ctypes
import os
import sys

from rich.console import Console
from rich.traceback import install as install_traceback

import utilities as _utils
from _PyStats import Stat, VisualWrapper

console = Console(record=True)

# Changed it to pystat_print because it wouldn't let me print other things that I wanted using
# the standard print statement
pystat_print = console.print

install_traceback(show_locals=False)

if __name__ == "__main__":

    os_name = os.name

    if os_name == "nt":
        # we only want this to be executed if the operating system is Windows
        # moved is_admin function to utilities.py
        if _utils.is_admin():
            print("Running the script with ADMIN privileges.")
        else:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv),
                                                None, 1)

    parser = argparse.ArgumentParser()

    # if no arguments are passed, the default is set to the current directory
    parser.add_argument("-df", help="Input Absolute Path to Directory or one File")

    # df is directory or file it will kinda figure out itself assuming theirs only 2 files in
    # the dir and u do -neglect
    parser.add_argument("-neglect", help="Input Absolute Path to File to Ignore ONLY IN DIRECTORY")

    # Argument if to get how many variables
    parser.add_argument("--vars", help="Get how many variables are in the file")

    # Argument to enable adhd mode
    parser.add_argument("--adhd", help="Enable ADHD Mode", default=False)

    # Argument to get line in get_functions in Stat class
    parser.add_argument("--getline",
                        help="Get Help line in Functions (Disabled cause it makes it extremely "
                             "big)",
                        default=False)

    parser.add_argument("-imgpath", help="Input Absolute Path to create the img example: \
                        file_name (dont add anything else)", default=None)

    # Debug argument to print out the file names
    path = parser.parse_args()
    args = parser.parse_args()

    if args.vars is None:
        args.vars = False
    if args.df is None:
        # using different separators for windows and linux
        separator = "\\" if os_name == "nt" else "/"

        # get file paths
        working_path = [f"{os.getcwd()}{separator}{py_file}"
                        for py_file in os.listdir(os.getcwd())
                        if os.path.isfile(py_file) and py_file.endswith(".py")]

        # get relative paths (full paths are too big)
        working_path = [os.path.relpath(path) for path in working_path]

        # sort
        working_path.sort()

        # Automatic mode
        print("Currently in Automatic mode this selects all files only in your current directory "
              "ending with py extension")
    else:
        # Determine if it's a directory or file
        if os.path.isdir(path.df):
            working_path = [[os.path.relpath(os.path.join(dir_path, f))
                             for f in filenames if f.endswith('.py')]
                            for dir_path, _, filenames in os.walk(path.df)]

            # remove neglect from paths
            if path.neglect is not None:
                for line in working_path:
                    original_line = line
                    line = line.replace("\\", "/")
                    if path.neglect in line:
                        working_path.remove(original_line)
        else:
            working_path = path.df

old_info = Stat(working_path)
info = VisualWrapper(working_path)
if args.adhd:
    info = VisualWrapper(working_path)

if args.imgpath:
    info.img_render(remove_check=False, force_show=True, clear_screen=True)
else:
    pystat_print(info.get_all())
