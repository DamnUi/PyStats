import argparse
import ctypes
import itertools
import os
import random
import re
import sys

from rich import print
from rich.columns import Columns
from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.status import Status
from rich.traceback import install as install_traceback

import errors as _errors
import utilities as _utils

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


class Stat:
    def __init__(self, directory) -> None:
        # this is to accommodate projects with multiple directories as well as those with
        # multiple files in a single directory
        if _utils.is_nested_list(directory):
            self.directory = [os.path.relpath(dir_)
                              for dir_ in list(itertools.chain.from_iterable(directory))]
        elif isinstance(directory, list):
            self.directory = [os.path.relpath(dir_) for dir_ in directory]
        else:
            self.directory = [directory]

        self.directory.sort() if isinstance(self.directory, list) else self.directory

        # if no file is present, break the program efficiently
        if not self.directory:
            raise _errors.NoFilePresent("No file present in given directory.")
        else:
            dir_ = [x for x in self.directory if "__init__" in x]

        self.directory_details = [f"[u][green]{len(self.directory)} file(s) found in {len(dir_)} "
                                  f"folders:[/][/]\n"]


    @property
    def return_directory_details(self):
        return self.directory_details

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
            for file_path in self.directory:
                from_imp = _utils.from_imports(input_file=file_path, get_assets=get_assets)
                imp_ = _utils.import_imports(input_file=file_path)

                self.add_from_imports_results(from_import_list=from_imp, result_dictionary=result)
                self.add_imports_to_results(import_list=imp_, result_dictionary=result)
        else:
            from_imp = _utils.from_imports(input_file=self.directory[0], get_assets=get_assets)
            imp_ = _utils.import_imports(input_file=self.directory[0])

            self.add_from_imports_results(from_import_list=from_imp, result_dictionary=result)
            self.add_imports_to_results(import_list=imp_, result_dictionary=result)

        return result

    def __scrape_variables(self, full_line_of_variable=False):
        variables_ = [line_
                      for file_ in self.directory
                      for line_ in open(file_, encoding="utf-8")
                      if re.match(r"^\s*\w+\s=\s", line_) or re.match(r"^\s*self.\w+\s=\s", line_)] #\s*\w+\s=\s maybe ?

        list_of_variables = [variables.strip()
                             if full_line_of_variable
                             else variables.split("=")[0].strip().replace("self.", "")
                             for variables in variables_
                             if variables]

        #Remove dupelicates in list_ofvariables
        list_of_variables = list(set(list_of_variables))
        list_of_variables =  _utils.list_to_counter_dictionary(list_of_variables)
        


        for file_path in self.directory:
            with open(file_path, encoding="utf-8") as file:
                #Lines without \n
                lines = [line.strip() for line in file.readlines()]
                for varible in list_of_variables:
                    rgex = fr"(self.)?\b(?=\w){varible}\b(?!\w)"
                    for line in lines:
                        if re.search(rgex, line, re.IGNORECASE):
                            list_of_variables[varible] += 1


        return list_of_variables

    def import_count(self, get_assets=True):
        result = self.__scrape_imports(get_assets=get_assets)

        for key, value in result.items():
            if not isinstance(value, int):
                result[key] = _utils.list_to_counter_dictionary(value)

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
        item_list = _utils.list_to_counter_dictionary(self.__scrape_variables())

        if args.vars:
            n_variables = int(args.vars)

        most_used_variable = {key: value
                              for key, value in
                              sorted(item_list.items(), key=lambda item: item[1], reverse=True)}

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
            raise _errors.OutputNotSpecified("The out_import_type must be one of 'from', 'import', "
                                             "or 'all'.")

    def most_called_func(self):

        most_called_func = {}
        for file_path in self.directory:
            with open(file_path, encoding="utf8") as open_file:
                # lines without \n
                file_contents = [_.rstrip("\n") for _ in open_file]

                # func names with call '^\s*def\s+(\w+)\s*\('
                func_names = [re.match(r"^\s*def\s+(\w+)\s*\(", content).group(1)
                              for content in file_contents
                              if re.match(r"^\s*def\s+(\w+)\s*\(", content)]

                func_names = [f"{func_name}"
                              for func_name in func_names
                              if not func_name.endswith('__')]

                for each in func_names:
                    matched_lines = re.findall(rf"(?:def\s)?{each}\(", ''.join(file_contents))
                    most_called_func[each] = len(matched_lines) - 1

        # Sort by frequency of use
        most_called_func = {key: value
                            for key, value in
                            sorted(most_called_func.items(), key=lambda item: item[1],
                                   reverse=True)}

        # if frequency is 0 then replace it with text 'Only Defined'
        for key, value in most_called_func.items():
            if value == 0:
                most_called_func[key] = "[red]Defined Only[/]"

        return func_names, most_called_func

    def get_classes(self):
        class_names = {}
        for file_path in self.directory:
            cur_line = 1
            with open(file_path, encoding="utf8") as open_file:
                lines = [line.rstrip("\n") for line in open_file]
                file = open_file.name
                gex = re.compile(r"^\s*class\s+(\w+)\s*?(\S)([(|)]?.*)?(:$)?",
                                 re.MULTILINE | re.IGNORECASE)

                for line in lines:
                    line = line.strip()
                    line = str(line)
                    # could possibly also get the line where the class was defined
                    if gex.match(line):
                        class_name = gex.match(line).group(1)
                        class_names[class_name] = [line, f"Defined on line: {cur_line}",
                                                   f'and in file: {file}']
                    cur_line += 1

        return class_names

    def get_func(self, display_line=args.getline):
        # A full ripoff from the get_classes function with the only thing being changed is the regex
        class_names = {}
        for file_path in self.directory:
            cur_line = 1
            with open(file_path, encoding="utf8") as open_file:
                lines = [line.rstrip("\n") for line in open_file]
                file = open_file.name
                gex = re.compile(r"^\s*def\s+(\w+)\s*?(\S)([(|)]?.*)?(:$)?", re.MULTILINE |
                                 re.IGNORECASE)

                for line_ in lines:
                    line_ = str(line_.strip())
                    # could possibly also get the line where the class was defined
                    if gex.match(line_):
                        class_name = gex.match(line_).group(1)
                        if not class_name.endswith('__'):
                            if display_line:
                                class_names[class_name] = line_, f"[red]In file[/] {file} &" \
                                                                 f"[red]defined[/] " \
                                                                 f"@ line # {cur_line}"
                            else:
                                class_names[class_name] = f"[red]In file[/] {file} " f"[red]Defined[/] @ line {cur_line}"
                    cur_line += 1

        return class_names


class VisualWrapper:
    def __init__(self, directory, adhd_mode=False, extra_adhd=False) -> None:
        self.directory = directory
        self.stat = Stat(self.directory)
        self.adhd_mode = adhd_mode
        self.adhd_modev2 = extra_adhd

    @staticmethod
    def panel_print(object_to_render, border_style):
        return Panel(renderable=object_to_render, border_style=border_style)

    @staticmethod
    def get_random_color():
        good_colours = ["medium_spring_green",
                        "spring_green4",
                        "slate_blue1",
                        "indian_red",
                        "gold1",
                        "medium_purple2"]
        return random.choice(good_colours)

    def quick_stats(self):
        founds = self.stat.return_directory_details[0]

        if _utils.is_nested_list(self.directory):
            combined_directories = "\n".join(list(itertools.chain.from_iterable(self.directory)))
        elif isinstance(self.directory, list):
            combined_directories = "\n".join([f'{file_}' for file_ in self.directory])
        else:
            combined_directories = f'{self.directory}'
            
        quick_md = f"""{founds}[gold1]{combined_directories}[/]"""
        quick = Panel(renderable=quick_md,
                      title="[magenta][b]Files obtained[/]",
                      style='bright_blue')

        return quick

    def get_line_count(self):
        color1, color2 = self.get_colors()
        line_count = self.stat.line_count()

        line_count_md = "\n".join([f"[{color2}]{key}[/]: [{color1}]{value}[/]"
                                   for key, value in line_count.items()])

        line_count_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", line_count_md)

        line_count_md = f"""[pale_turquoise1]{line_count_md}[/]"""
        line_count_panel = Panel(renderable=line_count_md,
                                 title="[black]Line Count",
                                 title_align="left",
                                 border_style="blue")

        return line_count_panel

    def get_variable(self, n_variables=3):
        n_variables = len(self.directory)
        if int(n_variables) == 10:
            n_variables = 1
        if args.vars:
            n_variables = int(args.vars)
            # Gets max number of variables assuming their not more than 100000 cloud implement a
            # fix to this astro, but it will do for now
            # print(len(self.stat.most_used_variable(100000)))
            if int(n_variables) > int(len(self.stat.most_used_variable(100000))):
                n_variables = int(len(self.stat.most_used_variable(100000)))

        color1, color2 = self.get_colors()

        variables = self.stat.most_used_variable(n_variables)
        if n_variables is None:
            start = "Frequency of variables used"
        else:
            start = f"Listing top [b u]{n_variables}[/] variables used"

        # add \n after each element except after last element
        variables_md = "\n".join([f"[{color2}]{key}[/]: [{color1}]{value}[/]"
                                  for key, value in variables.items()])
        variables_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", variables_md)
        variable_md = f"""[pale_turquoise1]{variables_md}[/]"""
        variable_panel = Panel(renderable=variable_md,
                               title=f"[black]{start}",
                               title_align="left",
                               border_style="blue")

        return variable_panel

    def get_import_count(self):
        color1, color2 = self.get_colors()
        imports = self.stat.import_count()

        all_imports = imports
        imports = {k: v for k, v in imports.items() if k.startswith("import")}
        len_import_imports = len(imports)
        # add \n after each element except after last element
        imports_md = "\n".join([f"[{color2}]{k}[/]: [{color1}]{v}[/]" for k, v in imports.items()])

        imports_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", imports_md)
        import_md = f"""[pale_turquoise1]{imports_md}[/]"""

        imports_from = {k: v for k, v in all_imports.items() if k.startswith("from")}
        len_from_imports = len(imports_from)
        # add \n after each element except after last element
        imports_md_from = "\n".join([f"[{color2}]{key}[/]: [{color1}]{value}[/]"
                                     for key, value in imports_from.items()])
        imports_md_from = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", imports_md_from)
        import_md_from = f"""[pale_turquoise1]{imports_md_from}[/]"""

        learn = len_from_imports if len_import_imports < len_from_imports else len_import_imports

        import_panel = Panel(renderable=import_md,
                             title="[black]Count of 'import' statements",
                             title_align="left",
                             border_style="blue", )

        from_import_panel = Panel(renderable=import_md_from,
                                  title="[black]Count of 'from' statements",
                                  title_align="left",
                                  border_style="blue", )

        return import_panel, from_import_panel

    def get_most_called_func(self):
        color1, color2 = self.get_colors()

        func_names, most_called_func = self.stat.most_called_func()

        func_names_md = "\n".join([f"[{color2}]{key}[/]: [{color1}]{value}[/]"
                                   for key, value in most_called_func.items()])

        func_names_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", func_names_md)

        func_names_md = f"""[pale_turquoise1]{func_names_md}[/]"""
        func_panel = Panel(renderable=func_names_md,
                           title="[black]Most Called Functions [red][/]",
                           title_align="left",
                           border_style="blue")

        return func_panel

    def get_class(self):
        color1, color2 = self.get_colors()
        classes = self.stat.get_classes()
        # add \n after each element except after last element
        classes_md = "\n".join([f"[{color2}]{k}[/]: [{color1}]{v}[/]" for k, v in classes.items()])
        classes_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", classes_md)
        class_md = f"""[pale_turquoise1]{classes_md}[/]"""
        class_panel = Panel(renderable=class_md,
                            title="[black]Classes",
                            title_align="left",
                            border_style="blue")

        return class_panel

    def get_func(self):
        color1, color2 = self.get_colors()
        func = self.stat.get_func()
        # add \n after each element except after last element
        func_md = "\n".join([f"[{color2}]{key}[/]: [{color1}]{value}[/]"
                             for key, value in func.items()])
        func_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", func_md)
        func_md = f"""[pale_turquoise1]{func_md}[/]"""
        func_panel = Panel(renderable=func_md,
                           title="[black]Functions",
                           title_align="left",
                           border_style="blue")

        return func_panel

    def get_colors(self):
        color1 = self.get_random_color() if self.adhd_mode else 'bright_blue'
        color2 = self.get_random_color() if self.adhd_modev2 else 'bright_green'

        return color1, color2

    def get_all(self):
        # remove \n from self.stat.return_directory_details()
        return_founds = self.stat.return_directory_details
        with Status(f'[black]Analyzing code with {return_founds[0]}[/], '
                    f'Selected files [green]{self.directory}[/]'):
            imp_count = self.get_import_count()

            group1 = Columns([self.get_line_count(), self.get_variable(), self.get_class()])

            group2 = Columns([imp_count[0], imp_count[1]], padding=(0, 1))

            group3 = Columns([self.get_func(), self.get_most_called_func()])

            groups = Group(self.quick_stats(), Rule('[black]At a glance'), group1,
                           Rule('[black]Functions', style='red'), group3,
                           Rule('[black]Imports', style='yellow'),
                           group2)

            return Panel(renderable=groups, title="[black]All Stats", title_align="center",
                         width=None, style=self.get_random_color())


old_info = Stat(working_path)
info = VisualWrapper(working_path)
if args.adhd:
    info = VisualWrapper(working_path, adhd_mode=True, extra_adhd=True)

print(info.get_all())
# test
