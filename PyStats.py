import argparse
import ctypes
import itertools
import os
import re
import sys

from rich import pretty, print
from rich.traceback import install as install_traceback

from utilities import from_imports, import_imports, is_admin, list_to_counter_dictionary

pretty.install()
install_traceback(show_locals=False)

if __name__ == '__main__':

    os_name = os.name

    if os_name == 'nt':
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
    parser.add_argument('-onefile', help="Input Absolute Path to File to Analyze")
    parser.add_argument("-neglect", help="Input Absolute Path to File to Ignore ONLY IN DIRECTORY")
    # Debug argument to print out the file names
    path = parser.parse_args()
    args = parser.parse_args()
    # 2 Variables
    # path.df
    # path.onefile ignores everything and makes sure u have just onefile ur scanning
    # Path.neglect

    if not any(vars(args).values()):
        # using different separators for windows and linux
        separator = '\\' if os_name == 'nt' else '/'

        # get file paths
        paths = [f'{os.getcwd()}{separator}{py_file}' for py_file in os.listdir(os.getcwd()) if
                 os.path.isfile(py_file) and py_file.endswith('.py')]

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
            paths = []
            for dir_path, _, filenames in os.walk(path.df):
                for f in filenames:
                    if f.endswith('.py'):
                        paths.append(os.path.abspath(os.path.join(dir_path, f)))
            # remove neglect from paths
            if path.neglect is not None:
                for line in paths:
                    original_line = line
                    line = line.replace("\\", "/")
                    if path.neglect in line:
                        paths.remove(original_line)
        else:
            paths = [path.df]
    # That ends classification of the file


class OutputNotSpecified(Exception):
    pass


class Stat:
    def __init__(self, directory) -> None:
        self.directory = [os.path.relpath(x) for x in directory]
        self.directory.sort()
        # Check if file exists
        if not all([x for x in self.directory]):
            print("[red]No file present in given directory.")
            exit()
        else:
            dir_ = [x for x in self.directory if '__init__' in x]
            print(f"[green]{len(self.directory)} files found in {len(dir_)} folders.\n")
            # print("[yellow]Exploring further ...\n")

    @staticmethod
    def add_imports_to_results(import_list, result_dictionary):
        for key, value in import_list.items():
            if key not in result_dictionary.keys():
                result_dictionary[key] = value
            else:
                result_dictionary[key] += value

    @staticmethod
    def add_from_results(from_import_list, result_dictionary):
        for key, value in from_import_list.items():
            if key not in result_dictionary.keys():
                result_dictionary[key] = value
            else:
                result_dictionary[key].extend(value)

    def __scrape_imports(self, get_assets=True):
        result = {}
        if len(self.directory) > 1:
            print("[blue]Scraping imports from multiple files...\n")
            if get_assets:
                print('[blue]Calculating assets ...\n')
            for file_path in self.directory:
                from_imp = from_imports(input_file=file_path, get_assets=get_assets)
                imp_ = import_imports(input_file=file_path)

                self.add_from_results(from_import_list=from_imp, result_dictionary=result)

                self.add_imports_to_results(import_list=imp_, result_dictionary=result)
        else:
            print("[blue]Scraping imports from single file...\n")
            from_imp = from_imports(input_file=self.directory[0], get_assets=get_assets)
            imp_ = import_imports(input_file=self.directory[0])

            self.add_from_results(from_import_list=from_imp, result_dictionary=result)

            self.add_imports_to_results(import_list=imp_, result_dictionary=result)

        return result

    def __scrape_variables(self, full_line_of_variable=False):
        variables_ = [line_
                      for file_ in self.directory
                      for line_ in open(file_, encoding='utf-8')
                      if re.match('^\s*\w+\s=\s', line_) or re.match('^\s*self.\w+\s=\s', line_)]

        list_of_variables = [variables.strip()
                             if full_line_of_variable
                             else variables.split('=')[0].strip().replace('self.', '')
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
                with open(file_path, encoding='utf8') as open_file:

                    # taken from https://stackoverflow.com/a/19001477
                    # using generator expression, a LARGE file can also be read without
                    # using too much physical memory of the system

                    if not exclude_empty_line:
                        count = sum(1 for _ in open_file)
                    else:
                        count = sum(1 for _ in open_file if _.rstrip('\n'))

                    file_path = file_path.split('../')[1] if '..' in file_path else file_path
                    line_count[file_path] = count
        else:
            with open(self.directory[0], encoding='utf8') as open_file:
                file_path = os.path.relpath(self.directory[0])
                line_count[file_path] = sum(1 for _ in open_file)

        return line_count

    def most_used_variable(self, n_variables=None):
        if n_variables is None:
            start = 'Frequency of variables used'
        else:
            start = f'Listing top {n_variables} variables used'

        print(f'[magenta]{start}.\n')

        most_used_variable = {key: value for key, value in
                              sorted(list_to_counter_dictionary(self.__scrape_variables()).items(),
                                     key=lambda item: item[1], reverse=True)}

        if n_variables is not None:
            return {k: v for k, v in list(most_used_variable.items())[:n_variables]}
        else:
            return most_used_variable

    def get_import_names(self, import_type: str = 'all'):
        all_imports = []
        imports = self.import_count()

        from_ = [[k_ for k_ in v.keys()] for k, v in imports.items() if 'from' in k]
        from_ = list(set(itertools.chain.from_iterable(from_)))
        from_.sort()

        import_ = [k.split('import')[1].strip() for k in imports.keys() if 'import' in k]
        import_.sort()

        if import_type == 'from':
            return from_
        elif import_type == 'import':
            return import_
        elif import_type == 'all':
            all_ = list(itertools.chain.from_iterable([from_, import_]))

            all_imports.extend(all_)
            all_imports = list(set(all_imports))
            all_imports.sort()

            return all_imports
        else:
            raise OutputNotSpecified('The out_import_type must be one of \'from\', \'import\', '
                                     'or \'all\'.')


info = Stat(paths)
print(info.line_count())
print(info.most_used_variable())
# print(info.scrape_imports())
#       info.most_used_variable(),
#       info.scrape_variables())
