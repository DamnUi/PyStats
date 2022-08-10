import argparse
import ctypes
import itertools
import os
import random
import re
import sys

from rich import print
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.status import Status
from rich.traceback import install as install_traceback

from utilities import from_imports, import_imports, is_admin, list_to_counter_dictionary

console = Console()
# print = console.print

install_traceback(show_locals=False)

if __name__ == "__main__":

    os_name = os.name

    if os_name == "nt":
        # we only want this to be executed if the operating system is Windows
        # moved is_admin function to utilities.py
        if is_admin():
            print("Running the script with ADMIN privileges.")
        else:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv),
                                                None, 1)

    parser = argparse.ArgumentParser()

    # if no arguments are passed, the default is set to the current directory
    parser.add_argument("-df", help="Input Absolute Path to Directory or File")

    # df is directory or file it will kinda figure out itself assuming theirs only 2 files in
    # the dir and u do -neglect
    parser.add_argument("-onefile", help="Input Absolute Path to File to Analyze")
    parser.add_argument("-neglect", help="Input Absolute Path to File to Ignore ONLY IN DIRECTORY")

    # Argument if to get how many variables
    parser.add_argument("--vars", help="Get how many variables are in the file")

    # Debug argument to print out the file names
    path = parser.parse_args()
    args = parser.parse_args()

    if args.vars is None:
        args.vars = False
    if not any(vars(args).values()):
        # using different separators for windows and linux
        separator = "\\" if os_name == "nt" else "/"

        # get file paths
        paths = [f"{os.getcwd()}{separator}{py_file}"
                 for py_file in os.listdir(os.getcwd())
                 if os.path.isfile(py_file) and py_file.endswith(".py")]

        # get relative paths (full paths are too big)
        paths = [os.path.relpath(path) for path in paths]

        # sort
        paths.sort()

        # Automatic mode
        print("Currently in Automatic mode this selects all files only in your current directory "
              "ending with py extension")
    elif path.onefile:
        paths = [path.onefile]
    else:
        # Determine if it's a directory or file
        if os.path.isdir(path.df):
            # If it's a directory get all absolute paths of files in it ending with py
            paths = [[os.path.abspath(os.path.join(dir_path, f))
                      for f in filenames if f.endswith('.py')]
                     for dir_path, _, filenames in os.walk(path.df)]

            # remove neglect from paths
            if path.neglect is not None:
                for line in paths:
                    original_line = line
                    line = line.replace("\\", "/")
                    if path.neglect in line:
                        paths.remove(original_line)
        else:
            paths = [path.df]


class OutputNotSpecified(Exception):
    pass


class Stat:
    def __init__(self, directory) -> None:
        self.directory = [os.path.relpath(x) for x in directory]
        self.directory.sort()
        self.founds = []
        # Check if file exists
        if not all([x for x in self.directory]):
            self.founds.append("[red]No file present in given directory.")
            exit()
        else:
            dir_ = [x for x in self.directory if "__init__" in x]
            self.founds.append(f"[green]{len(self.directory)} files found in {len(dir_)} "
                               f"folders.\n")

    def return_founds(self):
        return self.founds

    @staticmethod
    def add_imports_to_results(import_list, result_dictionary):
        for key, value in import_list.items():
            if key not in result_dictionary.keys():
                result_dictionary[key] = value
            else:
                result_dictionary[key] += value

    @staticmethod
    def add_from_imports_results(from_import_list, result_dictionary):
        for key, value in from_import_list.items():
            if key not in result_dictionary.keys():
                result_dictionary[key] = value
            else:
                result_dictionary[key].extend(value)

    def __scrape_imports(self, get_assets=True):
        result = {}
        if len(self.directory) > 1:
            with Status('[blue]Scraping imports from multiple files...'):
                # if get_assets:
                #     print('[blue]Calculating assets ...\n')
                for file_path in self.directory:
                    from_imp = from_imports(input_file=file_path, get_assets=get_assets)
                    imp_ = import_imports(input_file=file_path)

                    self.add_from_imports_results(from_import_list=from_imp,
                                                  result_dictionary=result)

                    self.add_imports_to_results(import_list=imp_, result_dictionary=result)
        else:
            with Status('[blue]Scraping imports from single file...'):
                from_imp = from_imports(input_file=self.directory[0], get_assets=get_assets)
                imp_ = import_imports(input_file=self.directory[0])

                self.add_from_imports_results(from_import_list=from_imp, result_dictionary=result)

                self.add_imports_to_results(import_list=imp_, result_dictionary=result)

        return result

    def __scrape_variables(self, full_line_of_variable=False):
        variables_ = [line_
                      for file_ in self.directory
                      for line_ in open(file_, encoding="utf-8")
                      if re.match("^\s*\w+\s=\s", line_) or re.match("^\s*self.\w+\s=\s", line_)]

        list_of_variables = [variables.strip()
                             if full_line_of_variable
                             else variables.split("=")[0].strip().replace("self.", "")
                             for variables in variables_
                             if variables]

        return list_of_variables

    def import_count(self, get_assets=True):
        result = self.__scrape_imports(get_assets=get_assets)

        for key, value in result.items():
            if not isinstance(value, int):
                result[key] = list_to_counter_dictionary(value)

        return dict(sorted(result.items(), reverse=True))

    def line_count(self, exclude_empty_line: bool = False):
        line_count = {}
        # if it's a directory return the lines in a dict with the relative file name as the key
        if len(self.directory) > 1:
            for file_path in self.directory:
                # changed the full file name to a relative path for easier viewing/showing
                file_path = os.path.relpath(file_path)
                with open(file_path, encoding="utf8") as open_file:

                    # taken from https://stackoverflow.com/a/19001477
                    # using generator expression, a LARGE file can also be read without
                    # using too much physical memory of the system

                    if not exclude_empty_line:
                        count = sum(1 for _ in open_file)
                    else:
                        count = sum(1 for _ in open_file if _.rstrip("\n"))

                    file_path = (file_path.split("../")[1] if ".." in file_path else file_path)
                    line_count[file_path] = count
        else:
            with open(self.directory[0], encoding="utf8") as open_file:
                file_path = os.path.relpath(self.directory[0])
                line_count[file_path] = sum(1 for _ in open_file)

        return line_count

    def most_used_variable(self, n_variables=None):
        if args.vars:
            n_variables = int(args.vars)
        # if n_variables is None:
        #     start = 'Frequency of variables used'
        # else:
        #     start = f'Listing top {n_variables} variables used'

        # print(f'[pale_turquoise1]{start}.\n')

        most_used_variable = {key: value
                              for key, value in
                              sorted(list_to_counter_dictionary(self.__scrape_variables()).items(),
                                     key=lambda item: item[1],
                                     reverse=True)}

        if n_variables is not None:
            return {key: value for key, value in list(most_used_variable.items())[:n_variables]}
        else:
            return most_used_variable

    def get_import_names(self, import_type: str = "all"):
        all_imports = []
        imports = self.__scrape_imports(get_assets=True)

        from_ = [k for k in imports.keys() if "from" in k]
        # sort by frequency of imports
        from_.sort()

        import_ = [k for k in imports.keys() if "import" in k]
        # Sort by frequency of import
        import_.sort(key=lambda x: imports[x], reverse=True)
        import_.sort()

        if import_type == "from":
            return from_
        elif import_type == "import":
            return import_
        elif import_type == "all":
            all_ = list(itertools.chain.from_iterable([from_, import_]))

            all_imports.extend(all_)
            all_imports = list(set(all_imports))
            all_imports.sort()

            return all_imports
        else:
            raise OutputNotSpecified("The out_import_type must be one of 'from', 'import', "
                                     "or 'all'.")

    def most_called_func(self):

        most_called_func = {}
        for file_path in self.directory:
            with open(file_path, encoding="utf8") as open_file:
                # lines without \n
                lines = [line.rstrip("\n") for line in open_file]

                # func names with call '^\s*def\s+(\w+)\s*\('
                func_names = [re.match("^\s*def\s+(\w+)\s*\(", line).group(1)
                              for line in lines
                              if re.match("^\s*def\s+(\w+)\s*\(", line)]
                # add () to func_names
                func_names = [f"{func_name}()" for func_name in func_names]

                for line in lines:
                    for each in func_names:
                        if each in line:
                            most_called_func[each] = most_called_func.get(each, 0) + 1

        # Sort by frequency of use
        most_called_func = {key: value
                            for key, value in
                            sorted(most_called_func.items(), key=lambda item: item[1],
                                   reverse=True)}

        # if frequency is 1 then replace it with text 'Only Defined'
        for key, value in most_called_func.items():
            if value == 1:
                most_called_func[key] = "[red]Defined Only[/]"
        return func_names, most_called_func


# Really bad code form here! yayy


class VisualWrapper:
    def __init__(self, directory, adhd_mode=False, extra_adhd=False) -> None:
        self.directory = directory
        self.stat = Stat(self.directory)
        self.adhd_mode = adhd_mode
        self.adhd_modev2 = extra_adhd

    @staticmethod
    def panel_print(thing, border_style):
        return Panel(thing, border_style=border_style)

    @staticmethod
    def get_random_colour():
        good_colours = ["medium_spring_green",
                        "spring_green4",
                        "slate_blue1",
                        "indian_red",
                        "gold1",
                        "medium_purple2"]
        return random.choice(good_colours)

    def quick_stats(self):
        founds = self.stat.return_founds()
        self.quick_md = f"""{founds[0]}[/][u]Selected Files[/]: [b]{self.directory}[/]"""
        self.quick = Align(renderable=Panel(renderable=Align(renderable=self.quick_md,
                                                             align="center"),
                                            title="Quick Stat",
                                            title_align="center"),
                           align="left",
                           style="black")  # Can Change border style here by changing style

        return self.quick

    def get_line_count(self):
        if self.adhd_mode:
            coul = self.get_random_colour()
        else:
            coul = "grey63"
        if self.adhd_modev2:
            coulv2 = self.get_random_colour()
        else:
            coulv2 = "pale_turquoise1"

        called = self.stat.line_count()
        called_md = "\n".join([f"[{coulv2}]{k}[/]: [{coul}]{v}[/]" for k, v in called.items()])

        called_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", called_md)

        self.line_count_md = f"""[pale_turquoise1]{called_md}[/]"""
        self.line_count_panel = Panel(renderable=self.line_count_md,
                                      title="[black]Line Count",
                                      title_align="left",
                                      border_style="blue")

        return self.line_count_panel

    def get_variable(self, n_variables=3):
        if args.vars:
            n_variables = int(args.vars)
            # Gets max number of variables assuming their not more than 100000 cloud implement a
            # fix to this astro, but it will do for now
            print(len(self.stat.most_used_variable(100000)))
            if int(n_variables) > int(len(self.stat.most_used_variable(100000))):
                n_variables = int(len(self.stat.most_used_variable(100000)))

        if self.adhd_mode:
            coul = self.get_random_colour()
        else:
            coul = "grey63"

        variables = self.stat.most_used_variable(n_variables)
        if n_variables is None:
            start = "Frequency of variables used"
        else:
            start = f"Listing top [b u]{n_variables}[/] variables used"

        if self.adhd_modev2:
            coulv2 = self.get_random_colour()
        else:
            coulv2 = "pale_turquoise1"
        # add \n after each element except after last element
        variables_md = "\n".join([f"[{coulv2}]{key}[/]: [{coul}]{value}[/]"
                                  for key, value in variables.items()])
        variables_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", variables_md)
        self.variable_md = f"""[pale_turquoise1]{variables_md}[/]"""
        self.variable_panel = Panel(renderable=self.variable_md,
                                    title=f"[black]{start}",
                                    title_align="left",
                                    border_style="blue")

        return self.variable_panel

    def get_import_count(self):
        learn = 0
        if self.adhd_mode:
            coul = self.get_random_colour()
        else:
            coul = "grey63"
        if self.adhd_modev2:
            coulv2 = self.get_random_colour()
        else:
            coulv2 = "pale_turquoise1"
        imports = self.stat.import_count()

        all_imports = imports
        imports = {k: v for k, v in imports.items() if k.startswith("import")}
        len_import_imports = len(imports)
        # add \n after each element except after last element
        imports_md = "\n".join([f"[{coulv2}]{k}[/]: [{coul}]{v}[/]" for k, v in imports.items()])

        imports_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", imports_md)
        self.import_md = f"""[pale_turquoise1]{imports_md}[/]"""
        self.import_panel = Panel(renderable=self.import_md,
                                  title="[black]Count of 'import' statements",
                                  title_align="left",
                                  border_style="blue",
                                  height=learn)

        imports_from = {k: v for k, v in all_imports.items() if k.startswith("from")}
        len_from_imports = len(imports_from)
        # add \n after each element except after last element
        imports_md_from = "\n".join([f"[{coulv2}]{key}[/]: [{coul}]{value}[/]"
                                     for key, value in imports_from.items()])
        imports_md_from = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", imports_md_from)
        self.import_md_from = f"""[pale_turquoise1]{imports_md_from}[/]"""

        self.from_imports = Panel(renderable=self.import_md_from,
                                  title="[black]Count of 'from' statements",
                                  title_align="left",
                                  border_style="blue",
                                  height=learn)

        if len_import_imports > len_from_imports:
            learn = len_import_imports
        elif len_import_imports < len_from_imports:
            learn = len_from_imports

        self.import_panel = Panel(renderable=self.import_md,
                                  title="[black]Count of 'import' statements",
                                  title_align="left",
                                  border_style="blue",
                                  height=learn + 2)

        self.from_imports = Panel(renderable=self.import_md_from,
                                  title="[black]Count of 'from' statements",
                                  title_align="left",
                                  border_style="blue",
                                  height=learn + 2)

        return self.import_panel, self.from_imports

    def get_most_called_func(self):
        func_names, most_called_func = self.stat.most_called_func()
        if self.adhd_mode:
            coul = self.get_random_colour()
        else:
            coul = "grey63"
        if self.adhd_modev2:
            coulv2 = self.get_random_colour()
        else:
            coulv2 = "pale_turquoise1"
        # add \n after each element except after last element

        func_names_md = "\n".join([f"[{coulv2}]{k}[/]: [{coul}]{v}[/]"
                                   for k, v in most_called_func.items()])

        func_names_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", func_names_md)

        self.func_md = f"""[pale_turquoise1]{func_names_md}[/]"""
        self.func_panel = Panel(renderable=self.func_md,
                                title="[black]Most Called Functions",
                                title_align="left",
                                border_style="blue")

        return self.func_panel

    def get_all(self):
        imp_count = self.get_import_count()
        grp = Columns([self.get_line_count(), self.get_variable()])
        grp2 = Columns([imp_count[0],
                        imp_count[1]], padding=(0, 1))
        mygrp = Group(self.quick_stats(), Rule('[black]Stats'), grp, self.get_most_called_func(),
                      grp2)

        return Panel(renderable=mygrp, title="[black]All Stats", title_align="center", width=None)


old_info = Stat(paths)
info = VisualWrapper(paths, adhd_mode=True)

print(info.get_all())

# print(info.quick_stats())
# print(info.get_line_count())
# print(info.get_variable())
