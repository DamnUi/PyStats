"""Created on Aug 27 17:22:45 2022."""

import argparse
import ast
import ctypes
import itertools
import os
import random
import re
import sys

from rich.columns import Columns
from rich.console import Console
from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.status import Status
from rich.traceback import install as install_traceback
from rich.tree import Tree

import errors as _errors
import utilities as _utils

# could've imported from PyStats but that'd create a circular import, should be avoided
console = Console(record=True)
install_traceback(show_locals=False)

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

        # if no file is present, break the program efficiently
        if not self.directory:
            raise _errors.NoFilePresent("No file present in given directory.")

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
                      if re.match(r"^\s*\w+\s=\s", line_)
                      or re.match(r"^\s*self.\w+\s=\s", line_)]  # \s*\w+\s=\s maybe ?

        list_of_variables = [variables.strip()
                             if full_line_of_variable
                             else variables.split("=")[0].strip().replace("self.", "")
                             for variables in variables_
                             if variables]

        # Remove duplicates in list_of_variables
        list_of_variables = list(set(list_of_variables))
        list_of_variables = _utils.list_to_counter_dictionary(list_of_variables)

        for file_path in self.directory:
            with open(file_path, encoding="utf-8") as file:
                lines = [_line.strip() for _line in file.readlines()]
                for variable in list_of_variables:
                    regex = fr"(self.)?\b(?=\w){variable}\b(?!\w)"
                    for line_ in lines:
                        if re.search(regex, line_, re.IGNORECASE):
                            list_of_variables[variable] += 1

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

        most_used_variable = dict(sorted(item_list.items(), key=lambda item: item[1], reverse=True))
        # Subtract 1 from each element in most_used_variable
        most_used_variable = {key: value - 1 for key, value in
                              most_used_variable.items()}  # It shows 1 extra var so

        # total number of defined vars
        total_vars = len(most_used_variable.keys())

        if n_variables is not None:
            return dict(list(most_used_variable.items())[:n_variables])
        else:
            return most_used_variable

    def get_import_names(self, import_type: str = "all"):
        all_imports = []
        imports = self.__scrape_imports(get_assets=True)

        from_ = [k for k in imports if "from" in k]
        # sort by frequency of imports
        from_.sort()

        import_ = [k for k in imports if "import" in k]
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
        most_called_func = dict(sorted(most_called_func.items(), key=lambda item: item[1],
                                       reverse=True))

        # if frequency is 0 then replace it with text 'Only Defined'

        return func_names, most_called_func

    def get_classes(self):
        class_names = {}
        ls = []
        itr = 0
        for file_path in self.directory:
            cur_line = 1

            with open(file_path, encoding="utf-8") as open_file:
                lines = [line.rstrip("\n") for line in open_file]
                file = open_file.name
                gex = re.compile(r"^\s*class\s+(\w+)\s*?(\S)([(|)]?.*)?(:$)?",
                                 re.MULTILINE | re.IGNORECASE)

            with open(file_path, encoding='utf-8') as fml:
                code = fml.read()
                node = ast.parse(code)
                for each in ast.walk(node):
                    if isinstance(each, ast.ClassDef):
                        ls.append(each.body)

            for line in lines:
                line = line.strip()
                line = str(line)
                # could possibly also get the line where the class was defined
                if gex.match(line):
                    class_name = gex.match(line).group(1)

                    if isinstance(ls[itr][0], ast.Pass):
                        ls[itr].remove(ls[itr][0])

                    class_names[class_name] = [f'{line}, '
                                               f'Defined on line: {cur_line}, '
                                               f'in file: {file} '
                                               f'Contains {len(ls[itr])} functions.'][0]

                    itr += 1
                cur_line += 1

        return class_names

    def get_func(self, display_line=args.getline, get_=None):
        # A full ripoff from the get_classes function with the only thing being changed is the regex
        times_used = self.most_called_func()  # Only
        most_called_func = times_used[1]
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
                                class_names[class_name] = [f'{line_}, '
                                                           f'[red]In file[/] {file} & '
                                                           f'[red]Defined[/] @ line # '
                                                           f'{cur_line}'][0]
                            else:
                                class_names[class_name] = ["This is useless dont use 0 or nothing",
                                                           f'[cyan]{class_name}:[/]', f"{file}",
                                                           f"{cur_line}",
                                                           f"{(most_called_func[class_name]) + 1}"]
                                # + 1 so that it also counts the time its defined could delete this
                                # if not needed

                    class_names = dict(sorted(class_names.items(), key=lambda item: item[1][-1],
                                              reverse=True))

                    cur_line += 1
        if get_:
            req_class_names = []
            for idk in list(class_names.items()):
                req_class_names.append(idk[1][get_])
            return req_class_names

        return class_names

    def get_control_statements(self):
        mvars = self.most_used_variable()
        if_list, while_list, for_or_async_for_list = [], [], []
        with_list, try_list, variables = [], [], []
        for file_path in self.directory:
            with open(file_path, encoding="utf8") as open_file:
                node = ast.parse(open_file.read())
                for thing in ast.walk(node=node):
                    if isinstance(thing, ast.If):
                        if_list.append(thing)

                    if isinstance(thing, ast.While):
                        while_list.append(thing)

                    if isinstance(thing, (ast.For, ast.AsyncFor)):
                        for_or_async_for_list.append(thing)

                    if isinstance(thing, ast.With):
                        with_list.append(thing)

                    if isinstance(thing, ast.Try):
                        try_list.append(thing)

                    # I have checked several variables, and a lot of them are inconsistent with
                    # the counts, so I think we shouldn't include this one
                    # if isinstance(thing, ast.Assign):
                    #     variables.append(thing)
                    # I agree with this one, it's not very useful
        # Essentially the try list is somewhat wrong this small piece of code is to fix it,
        # it rounds up the given number of times the variable is used
        # try:
        #     tl = int(math.ceil(len(try_list) / 2))
        # except Exception:
        #     tl = len(try_list)  # why not use it if you've defined it here?

        return (len(if_list), len(while_list), len(for_or_async_for_list), len(with_list),
                len(try_list), len(mvars.keys()))

    def count_decorator(self):
        decorator_list = {}
        line_num = 1
        for file_path in self.directory:
            with open(file_path, encoding="utf8") as open_file:
                code = [line.rstrip("\n") for line in open_file]
                gex = re.compile(r"(^\s*@(\w+)\s*?(\S)([(|)]?.*)?(:$)?)",
                                 re.MULTILINE | re.IGNORECASE)
                for line in code:
                    # Get with line
                    line = line.strip()
                    line = str(line)
                    if gex.match(line):
                        curr_val = line_num
                        decorator_list[gex.match(line).group(1)] = decorator_list.get(
                                gex.match(line).group(1), 0) + 1

                    line_num += 1
        return decorator_list

    @staticmethod
    def get_args():
        # Get all commandline args and what value their currently on
        # listing the arguments with - first, and -- after them
        arg_list = {'-df': args.df,
                    '-neglect': args.neglect,
                    '-getline': args.getline,
                    '-imgpath': args.imgpath,
                    '--vars': args.vars,
                    '--adhd': args.adhd, }
        return arg_list


class VisualWrapper:
    def __init__(self, directory, adhd_mode=False, extra_adhd=False) -> None:
        self.directory = directory
        self.stat = Stat(self.directory)

        # what about the adhd mode?
        self.adhd_mode = adhd_mode
        self.adhd_modev2 = extra_adhd

    @staticmethod
    def clear_term():
        if os_name == "nt":
            os.system("cls")
        else:
            os.system("clear")

    @staticmethod
    def get_random_color():
        good_colours = ["medium_spring_green",
                        "spring_green4",
                        "slate_blue1",
                        "gold1",
                        "medium_purple2"]
        return random.choice(good_colours)

    def quick_stats(self):
        current_directory = os.getcwd()
        rel_path = os.path.relpath(current_directory)

        tree = Tree(f'[magenta b]:open_file_folder: {current_directory}[/]',
                    guide_style='red')
        # guide_style changes the colour of the lines that go to the files

        if _utils.is_nested_list(self.directory):
            combined_directories = "\n".join(list(itertools.chain.from_iterable(self.directory)))
        elif isinstance(self.directory, list):
            combined_directories = "\n".join([f'{file_}' for file_ in self.directory])
        else:
            combined_directories = f'{self.directory}'

        # iterate through combined_directories without any \n
        for py_files in combined_directories.split("\n"):
            tree.add(f'[gold1]{py_files}[/] '
                     f'[spring_green4]({round(os.path.getsize(py_files) / 1000, 2)} kB)[/]')

        return Panel(tree, title="[magenta b]Files obtained[/]", style='bright_blue')

    def get_line_count(self):
        color1, color2 = self.get_colors()
        line_count = self.stat.line_count()

        line_count_md = "\n".join([f"[{color2}]{key}[/]: [{color1}]{value}[/]"
                                   for key, value in line_count.items()])

        line_count_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", line_count_md)

        line_count_md = f"""{line_count_md}"""
        line_count_panel = Panel(renderable=line_count_md,
                                 title="[magenta b]Line Count[/]",
                                 title_align="center",
                                 border_style="bright_blue")

        return line_count_panel

    def get_variable(self):
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
            start = f"Top [b u]{n_variables}[/] variables used"

        # add \n after each element except after last element
        variables_md = "\n".join([f"[{color2}]{key}[/]: [{color1}]{value}[/]"
                                  for key, value in variables.items()])
        variables_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", variables_md)

        variable_panel = Panel(renderable=variables_md,
                               title=f"[magenta b]{start}[/]",
                               title_align="center",
                               border_style="bright_blue")

        return variable_panel

    def get_import_count(self):
        color1, color2 = self.get_colors()
        imports = self.stat.import_count()

        all_imports = imports
        imports = {k: v for k, v in imports.items() if k.startswith("import")}
        len_import_imports = len(imports)
        # add \n after each element except after last element
        imports_md = "\n".join([f"[{color2}]{key}[/]: [{color1}]{value}[/]"
                                for key, value in imports.items()])

        imports_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", imports_md)

        imports_from = {k: v for k, v in all_imports.items() if k.startswith("from")}
        len_from_imports = len(imports_from)
        # add \n after each element except after last element
        imports_md_from = "\n".join([f"[{color2}]{key}[/]: [{color1}]{value}[/]"
                                     for key, value in imports_from.items()])
        imports_md_from = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", imports_md_from)

        # Get the smaller of the two
        if len_import_imports < len_from_imports:
            difference = len_from_imports - len_import_imports
            for _ in range(difference):
                imports_md += "\n"
        else:
            difference = len_import_imports - len_from_imports
            # Add the difference as lines to the import_md
            for _ in range(difference):
                imports_md_from += "\n"

        import_panel = Panel(renderable=imports_md,
                             title="[black]Count of 'import' statements",
                             title_align="left",
                             border_style="blue", )

        from_import_panel = Panel(renderable=imports_md_from,
                                  title="[black]Count of 'from' statements",
                                  title_align="left",
                                  border_style="blue", )

        return import_panel, from_import_panel

    def get_class(self):
        color1, color2 = self.get_colors()
        classes = self.stat.get_classes()

        classes_md = "\n".join([f"[{color2}]{key}[/]: [{color1}]{value}[/]"
                                for key, value in classes.items()])
        classes_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", classes_md)

        class_panel = Panel(renderable=classes_md,
                            title="[magenta b]Classes",
                            title_align="left",
                            border_style="bright_blue")

        return class_panel

    def get_func(self, get_=None):
        color1, color2 = self.get_colors()
        func = self.stat.get_func(get_=get_)
        # add \n after each element except after last element
        try:
            func_md = "\n".join(
                    [f"[{color2}]{key}[/]: [{color1}]{value}[/]" for key, value in func.items()])
            func_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", func_md)

        except Exception as e:
            try:
                old_func = func
                func = ('\n'.join(func))
                if get_ == 1:
                    title = '[black]Function'
                    width = len(max(old_func))
                elif get_ == 2:
                    title = '[black]In File'
                    width = len(max(old_func)) + 4
                elif get_ == 3:
                    title = '[black]Line'
                    width = len(max(old_func)) * 10
                else:
                    title = '[black]Times Used'
                    width = len(max(old_func)) * 10
                func_panel = Panel(renderable=func,
                                   title=title,
                                   title_align="left",
                                   border_style="blue",
                                   width=width)
                return func_panel
            except Exception as e:
                print(e)
                pass

        func_panel = Panel(renderable=func,
                           title="[bright_black b]Functions[/]",
                           title_align="center",
                           border_style="red")

        return func_panel

    def get_statements(self):
        color1, color2 = self.get_colors()
        statements = self.stat.get_control_statements()
        statements_dict = {'If': statements[0],
                           'While': statements[1],
                           'For': statements[2],
                           'With': statements[3],
                           'Try': statements[4],
                           'Total defined variables': statements[5]}
        # again, I think we shouldn't have the Total defined variable

        statements_md = "\n".join([f"[{color2}]{key}[/]: [{color1}]{value}[/]"
                                   for key, value in statements_dict.items()])
        statements_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", statements_md)

        statements_panel = Panel(renderable=statements_md,
                                 title="[magenta b]Statements[/]",
                                 title_align="center",
                                 border_style="bright_blue")

        return statements_panel

    def get_deco(self):
        color1, color2 = self.get_colors()
        decorators = self.stat.count_decorator()

        decorators_md = "\n".join([f"[{color2}]{key}[/]: [{color1}]{value}[/]"
                                   for key, value in decorators.items()])
        decorators_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", decorators_md)

        decorators_panel = Panel(renderable=decorators_md,
                                 title="[magenta b]Decorators[/]",
                                 title_align="center",
                                 border_style="bright_blue")

        return decorators_panel

    def reformat_args(self):
        color1, color2 = self.get_colors()
        _args = self.stat.get_args()  # _args because args is a reserved keyword

        args_md = "\n".join([f"[{color2}]{key}[/]: [{color1}]{value}[/]"
                             for key, value in _args.items()])
        args_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", args_md)

        args_panel = Panel(renderable=args_md,
                           title="[magenta b]Running with arguments[/]",
                           title_align="center",
                           border_style="bright_blue")

        return args_panel

    def get_colors(self):
        color1 = self.get_random_color() if self.adhd_mode else 'bright_blue'
        color2 = self.get_random_color() if self.adhd_modev2 else 'bright_green'

        return color1, color2

    def img_render(self, remove_check=False, force_show=True, clear_screen=False):
        def get_info():
            print(self.get_all())
            if clear_screen:
                self.clear_term()

        if remove_check:
            get_info()

        if remove_check:
            with open(f'PyStats.svg ', 'w', encoding='utf-8') as f:
                f.write(console.export_svg())
                # open the file on Windows
                if force_show:
                    os.startfile(f'PyStats.svg')
                return 'Successfully rendered'
        if args.imgpath:
            get_info()
            with open(f'PyStats {args.imgpath}.svg ', 'w', encoding='utf-8') as f:
                f.write(console.export_svg())
                # open the file on Windows
                if force_show:
                    os.startfile(f'PyStats {args.imgpath}.svg')
                return 'Successfully rendered'
        else:
            return '[red]img render path not given - no image rendered \n' \
                   'Use the option --imgpath to specify a path[/]'

    def get_all(self, gui=True):

        with Status(f'[bright_black b]Analyzing code'
                    f'With files [bright_green]{self.directory}[/][/]'):
            imp_count = self.get_import_count()

            group1 = Columns([self.get_line_count(), self.get_variable(), self.get_deco(),
                              self.get_statements(), self.reformat_args()])

            group2 = Columns([imp_count[0], imp_count[1]], padding=(0, 1))

            group3 = Columns([self.get_func(1), self.get_func(4), self.get_func(3),
                              self.get_func(2)])  # The colours used for this need to change

            groups = Group(self.quick_stats(),
                           Rule('[bright_black b]At a glance[/]', style='red'),
                           group1, self.get_class(),
                           Rule('[bright_black b]Functions & Classes[/]', style='red'), group3,
                           Rule('[bright_black b]Imports (from count is not working currently)',
                                style='red'), group2)
            if gui:
                return Panel(renderable=groups,
                             title="[bright_black b]All Stats[/]",
                             title_align="center", style='red')
