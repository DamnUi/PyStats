"""PyStats - Python Code Statistics Analyzer

This module analyzes Python source code to provide statistics and insights about:
- Code structure (functions, classes, imports)
- Code metrics (line counts, complexity)
- Usage patterns (variable usage, function calls)
- Code duplication

The module can be used either as a command-line tool or imported as a library.
"""

# Standard library imports
from __future__ import annotations
from typing import Dict, List, Union, Optional, Any, Set, Tuple
import argparse
import ast
import ctypes
import itertools
import os
import random
import re
import sys
from pathlib import Path

# Third-party imports
import rich.box
from rich.columns import Columns
from rich.console import Console
from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.status import Status
from rich.traceback import install as install_traceback
from rich.tree import Tree
# install term charts later # Visualization library (in development)

# Local imports
import errors as _errors
import utilities as _utils

# Configuration
console = Console(record=True)
install_traceback(show_locals=False)
print = console.print

# Constants
SUPPORTED_EXTENSIONS = ['.py']
DEFAULT_ENCODING = 'utf-8'
MINIMUM_FILE_SIZE = 5000  # 5KB threshold for performance estimation

class FileProcessor:
    """Handles file discovery and validation for Python source files."""
    
    @staticmethod
    def find_python_files(directory: str) -> List[str]:
        """Find all Python files in the given directory.
        
        Args:
            directory: Root directory to search in
            
        Returns:
            List of paths to Python files found
        """
        python_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        return python_files
    
    @staticmethod
    def validate_python_file(file_path: str) -> bool:
        """Check if a Python file is valid by attempting to compile it.
        
        Args:
            file_path: Path to the Python file to validate
            
        Returns:
            True if file is valid Python, False otherwise
        """
        try:
            with open(file_path, 'r', encoding=DEFAULT_ENCODING) as f:
                compile(f.read(), file_path, 'exec')
            return True
        except Exception:
            return False
    
    @staticmethod
    def estimate_processing_time(file_paths: List[str]) -> int:
        """Estimate processing time based on file sizes.
        
        Args:
            file_paths: List of file paths to analyze
            
        Returns:
            Estimated processing time in seconds
        """
        total_time = 0
        for file_path in file_paths:
            size = os.path.getsize(file_path)
            if size < MINIMUM_FILE_SIZE:
                total_time += 2
            elif size < 10000:
                total_time += 4
            elif size < 20000:
                total_time += 5
            elif size < 30000:
                total_time += 6
            else:
                total_time += 10
        return total_time

def find(name: str, path: str) -> Optional[str]:
    """Find a file named *name* under *path* (expects no _utils in the directory)."""
    for root, _dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)
    return None


os_name = os.name


class PyStatsConfig:
    """Owns command-line arguments, file discovery and validation.

    This replaces the old pile of module-level ``parser`` / ``args`` /
    ``working_path`` / ``removed_files`` code that used to run (in a fragile
    order) at import time. Stat and VisualWrapper now share one config object
    instead of reaching for globals.
    """

    def __init__(self, argv: Optional[List[str]] = None) -> None:
        parser = self._build_argument_parser()
        self.args: argparse.Namespace = parser.parse_args(argv)
        if self.args.vars is None:
            self.args.vars = False
        self.removed_files: List[str] = []
        self.working_path: Union[List[str], List[List[str]], str] = self._discover_files()

    @staticmethod
    def _build_argument_parser() -> argparse.ArgumentParser:
        """Configure and return the argument parser (same flags as always)."""
        parser = argparse.ArgumentParser(
            description="Analyze Python source code and generate statistics"
        )
        # if arg nouments are passed, the default is set to the current directory
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
                            help="Get parameters of all scraped functions",
                            default=False)

        parser.add_argument("-imgpath", help="Input Absolute Path to create the img example: \
                            file_name (dont add anything else)", default=None)

        return parser

    def _discover_files(self) -> Union[List[str], List[List[str]], str]:
        """Find the python files to analyze.

        Fixes vs the old module-level code:
        - auto mode no longer removes files from the list *while iterating*
          over it (that silently skipped the file after every syntax error)
        - directory mode's -neglect filter actually works now (it used to
          mutate a throwaway loop variable instead of removing the file)
        - file validation uses the configured DEFAULT_ENCODING
        """
        if self.args.df is None:
            # Automatic mode - search current directory
            if __name__ == '__main__':
                print("[yellow]Currently in Automatic mode this selects all files only in your current directory "
                      "ending with py extension[/]")

            working_path = FileProcessor.find_python_files(os.getcwd())

            valid_files = []
            for file_path in working_path:
                if FileProcessor.validate_python_file(file_path):
                    valid_files.append(file_path)
                else:
                    self.removed_files.append(file_path)

            if __name__ == '__main__':
                print("[green]Found {} files in your current directory[/]".format(len(valid_files)))

            return valid_files

        if os.path.isdir(self.args.df):
            # Directory mode
            working_path: List[str] = []
            for dir_path, _dirnames, filenames in os.walk(self.args.df):
                working_path.extend(
                    os.path.relpath(os.path.join(dir_path, file_name))
                    for file_name in filenames
                    if file_name.endswith('.py')
                )

            # remove neglect from paths (this used to be broken, see docstring)
            if self.args.neglect is not None:
                working_path = [
                    file_path for file_path in working_path
                    if self.args.neglect not in file_path.replace("\\", "/")
                ]

            return working_path

        # Single file mode
        return self.args.df

    def ensure_admin(self) -> None:
        """Re-launch with admin privileges on Windows (no-op on other OSes).

        The old code did this as a side effect of *importing* _PyStats, which
        meant even importing the library triggered a UAC prompt.
        """
        if os_name != "nt" or _utils.is_admin():
            return
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable,
                                            " ".join(sys.argv), None, 1)

    def estimate_processing_time(self, file_paths: List[str]) -> int:
        """Estimate processing time based on file sizes (used by get_all)."""
        total_time = 0
        for file_path in file_paths:
            size = os.path.getsize(file_path)
            if size < MINIMUM_FILE_SIZE:
                total_time += 2
            elif size < 10000:
                total_time += 4
            elif size < 20000:
                total_time += 5
            elif size < 30000:
                total_time += 6
            elif size < 100000:
                total_time += 10
        return total_time





# Analysis-specific classes
class CodeReader:
    """Handles reading and caching of source code files."""
    
    def __init__(self, file_paths: List[str]):
        self.file_paths = file_paths
        self._cache: Dict[str, List[str]] = {}
        
    def get_file_contents(self, file_path: str) -> List[str]:
        """Get contents of a file, using cache if available."""
        if file_path not in self._cache:
            with open(file_path, encoding=DEFAULT_ENCODING) as f:
                self._cache[file_path] = f.readlines()
        return self._cache[file_path]

class ImportAnalyzer:
    """Analyzes Python import statements."""
    
    def __init__(self, code_reader: CodeReader):
        self.code_reader = code_reader
        
    def analyze_imports(self) -> Dict[str, Union[int, List[str]]]:
        """Analyze all import statements in the files.
        
        Returns:
            Dictionary containing import statistics:
            - Keys starting with 'import': Count of direct imports
            - Keys starting with 'from': List of imported names
        """
        result: Dict[str, Union[int, List[str]]] = {}
        
        for file_path in self.code_reader.file_paths:
            # Get imports using AST for more reliable parsing
            tree = ast.parse(''.join(self.code_reader.get_file_contents(file_path)))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        import_key = f"import {name.name}"
                        result[import_key] = result.get(import_key, 0) + 1
                        
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    from_key = f"from {module}"
                    if from_key not in result:
                        result[from_key] = []
                    imported = [n.name for n in node.names]
                    result[from_key] = list(set(result[from_key] + imported))  # type: ignore
                    
        return result

class VariableAnalyzer:
    """Analyzes Python variable declarations and usage."""
    
    def __init__(self, code_reader: CodeReader):
        self.code_reader = code_reader
        
    def analyze_variables(self) -> Dict[str, Dict[str, Any]]:
        """Analyze variable declarations and usage.
        
        Returns:
            Dictionary with variable statistics:
            {
                'variable_name': {
                    'type': str,  # Type of the variable if determinable
                    'count': int,  # Number of uses
                    'locations': List[Tuple[str, int]]  # File and line number of declarations
                }
            }
        """
        variables: Dict[str, Dict[str, Any]] = {}
        
        for file_path in self.code_reader.file_paths:
            tree = ast.parse(''.join(self.code_reader.get_file_contents(file_path)))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            var_name = target.id
                            if var_name not in variables:
                                variables[var_name] = {
                                    'type': type(node.value).__name__,
                                    'count': 0,
                                    'locations': []
                                }
                            variables[var_name]['count'] += 1
                            variables[var_name]['locations'].append(
                                (file_path, node.lineno)
                            )
                            
                elif isinstance(node, ast.Name):
                    if node.id in variables:
                        variables[node.id]['count'] += 1
                        
        return variables

class FunctionAnalyzer:
    """Analyzes Python function definitions and calls."""
    
    def __init__(self, code_reader: CodeReader):
        self.code_reader = code_reader
        
    def analyze_functions(self) -> Dict[str, Dict[str, Any]]:
        """Analyze function definitions and calls.
        
        Returns:
            Dictionary with function statistics:
            {
                'function_name': {
                    'calls': int,  # Number of times called
                    'params': List[str],  # Parameter names
                    'location': Tuple[str, int],  # File and line of definition
                    'decorators': List[str]  # Applied decorators
                }
            }
        """
        functions: Dict[str, Dict[str, Any]] = {}
        
        for file_path in self.code_reader.file_paths:
            tree = ast.parse(''.join(self.code_reader.get_file_contents(file_path)))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    name = node.name
                    if name not in functions:
                        functions[name] = {
                            'calls': 0,
                            'params': [arg.arg for arg in node.args.args],
                            'location': (file_path, node.lineno),
                            'decorators': [
                                ast.unparse(d).strip('@') for d in node.decorator_list
                            ]
                        }
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        if func_name in functions:
                            functions[func_name]['calls'] += 1
                            
        return functions

class CodeStatistics:
    """Main class for gathering and accessing code statistics."""
    
    def __init__(self, file_paths: List[str]):
        self.code_reader = CodeReader(file_paths)
        self.import_analyzer = ImportAnalyzer(self.code_reader)
        self.variable_analyzer = VariableAnalyzer(self.code_reader)
        self.function_analyzer = FunctionAnalyzer(self.code_reader)
        
        # Cache for analysis results
        self._import_stats: Optional[Dict] = None
        self._variable_stats: Optional[Dict] = None
        self._function_stats: Optional[Dict] = None
        
    def get_import_statistics(self) -> Dict[str, Union[int, List[str]]]:
        """Get statistics about imports."""
        if self._import_stats is None:
            self._import_stats = self.import_analyzer.analyze_imports()
        return self._import_stats
    
    def get_variable_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics about variables."""
        if self._variable_stats is None:
            self._variable_stats = self.variable_analyzer.analyze_variables()
        return self._variable_stats
    
    def get_function_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics about functions."""
        if self._function_stats is None:
            self._function_stats = self.function_analyzer.analyze_functions()
        return self._function_stats

class Stat:
    """Core statistics gathering class for Python source code analysis.
    
    This class handles parsing and analyzing Python source files to extract various
    statistics about code structure, usage patterns, and metrics.
    
    Attributes:
        directory: List of file paths to analyze
    """

    def __init__(self, directory: Union[str, List[str], List[List[str]]],
                 config: 'PyStatsConfig' = None) -> None:
        """Initialize the Stat class with target files to analyze.
        
        Args:
            directory: Path or list of paths to Python files to analyze
            
        Raises:
            NoFilePresent: If no valid files are found to analyze
        """
        if _utils.is_nested_list(directory):
            self.directory = [os.path.relpath(dir_)
                              for dir_ in list(itertools.chain.from_iterable(directory))]
        elif isinstance(directory, list):
            self.directory = [os.path.relpath(dir_) for dir_ in directory]
        else:
            self.directory = [directory]

        if not self.directory:
            raise _errors.NoFilePresent("No file present in given directory.")

        self._config = config if config is not None else _get_default_config()

    @staticmethod
    def add_imports_to_results(import_list: Dict[str, int], 
                             result_dictionary: Dict[str, int]) -> None:
        """Add import counts to results dictionary.
        
        Args:
            import_list: Dictionary of import statements and their counts
            result_dictionary: Target dictionary to update with counts
        """
        for key, value in import_list.items():
            if key not in result_dictionary:
                result_dictionary[key] = value
            else:
                result_dictionary[key] += value

    @staticmethod
    def add_from_imports_results(from_import_list: Dict[str, List[str]],
                               result_dictionary: Dict[str, List[str]]) -> None:
        """Add from-import results to the results dictionary.
        
        Args:
            from_import_list: Dictionary of from-import statements and imported names
            result_dictionary: Target dictionary to update
        """
        for key, value in from_import_list.items():
            if key not in result_dictionary:
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

                    try:
                        file_path = (file_path.split("../")[1] if ".." in file_path else file_path)
                    except IndexError:
                        file_path = file_path.split("/")[-1]
                        
                    line_count[file_path] = count
        else:
            file_path = os.path.relpath(self.directory[0])
            with open(self.directory[0], encoding="utf8") as open_file:
                if not exclude_empty_line:
                    line_count[file_path] = sum(1 for _ in open_file)
                else:
                    line_count[file_path] = sum(1 for _ in open_file if _.rstrip("\n"))

        if line_count:
            avg_line_count = round(sum(line_count.values()) / len(line_count.keys()), 2)
        else:
            avg_line_count = 0
        line_count["Average"] = avg_line_count

        return line_count

    def dupelinefind(self):
        self.dupes = {}
        for filepath in self.directory:
            #open every file get all lines make them hashes then find duplicates in all files
            with open(filepath, encoding="utf8") as open_file:
                lines = open_file.readlines()
                #strip line
                lines = [line.strip() for line in lines]
                
                for line in lines:
                    if line in self.dupes:
                        self.dupes[line] += 1
                    else:
                        self.dupes[line] = 1
                        
        #arrange them in order of most to least
        self.dupes = dict(sorted(self.dupes.items(), key=lambda item: item[1], reverse=True))
        #remove first value of dict
        self.dupes.pop('', None)
        
        return self.dupes

    def most_used_variable(self, n_variables=None):
        item_list = _utils.list_to_counter_dictionary(self.__scrape_variables())

        if self._config.args.vars:
            n_variables = int(self._config.args.vars)

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
        c1 = "spring_green4"
        c2 = "spring_green4"
        c3 = "spring_green4"
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
                    
                    try:
                        brackinfo = re.search(r'\((.*?)\)',line).group(1)
                        line = line.replace(brackinfo, f'[red]{brackinfo}[/]')
                        
                    except Exception:pass

                    if isinstance(ls[itr][0], ast.Pass):
                        ls[itr].remove(ls[itr][0])

                    
                    class_names[class_name] = [f'{line}, '
                                               f'- [{c1}]Defined on line: {cur_line}[/], '
                                               f'- [{c2}]in file: {file}[/] \n' 
                                               f' - [{c3}]Contains {len(ls[itr])} {"function" if len(ls[itr]) == 1 else "functions"}[/]'][0]# Yes this space is needed, and the [0] is needed too to remove brackets

                    itr += 1
                cur_line += 1

        return class_names

    def get_func(self, display_line=None, get_=None):
        # A full ripoff from the get_classes function with the only thing being changed is the regex
        if display_line is None:
            display_line = bool(getattr(self._config.args, 'getline', False))
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
                                #remove comments form line using regex
                                line_ = re.sub(r'#.*', '', line_)
                                #remove  : from line
                                line_ = line_.replace(':', '')
                                #using regex get all parameters and color them
                                for each in re.findall(r'\(.*?\)', line_):
                                    line_ = line_.replace(each, f'[magenta]{each}[/]')


                                class_names[class_name] = ["This is useless dont use 0 or nothing",
                                                           f'[cyan]{line_}:[/]', f"{file}",
                                                           f"{cur_line}",
                                                           f"{(most_called_func[class_name]) + 1}"]
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
    
    def get_var_types(self):
        var_types = {}
        numiter = 0
        for file_path in self.directory:
            with open(file_path, encoding="utf8") as open_file:
                tree = ast.parse(open_file.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                try:
                                    var_types[target.id] = type(node.value).__name__
                                except Exception:
                                    var_types[f"Cloudnt Get {numiter}"] = type(node.value).__name__
                            numiter += 1
        return var_types
        
    def get_args(self):
        # Get all commandline args and what value their currently on
        # listing the arguments with - first, and -- after them
        cfg_args = self._config.args
        arg_list = {'-df': cfg_args.df,
                    '-neglect': cfg_args.neglect,
                    '-getline': cfg_args.getline,
                    '-imgpath': cfg_args.imgpath,
                    '--vars': cfg_args.vars,
                    '--adhd': cfg_args.adhd, }
        return arg_list


## Wanted to split the long variable panel but cloudnt this code doesnt work
class custom_panel():
    def __init__(self, raw_md, splitbynewline=False) -> None:
        self.raw = raw_md
        if splitbynewline:
            self.raw = self.raw.split("\n")
    def set_panel_settings(self, title, border_style, expand=False, padding=(0, 0), width=100, height=100, title_align="center"):
        self.title = title
        self.border_style = border_style
        self.expand = expand
        self.padding = padding
        self.width = width
        self.height = height
        self.title_align = title_align
    
    def md_split(self, split_divide_by=3, dict_=False):
        self.split_divide_by = split_divide_by

        if dict_:
            items = list(self.raw.items()) if isinstance(self.raw, dict) else list(self.raw)
            return [items[i:i + 10] for i in range(0, len(items), 10)]

        if not split_divide_by:
            return [self.raw]

        contain = int(round(len(self.raw) / split_divide_by, 0))
        md_split = []
        for i in range(split_divide_by):
            md_split.append(self.raw[i * contain:(i + 1) * contain])
        return md_split

    def make_panel(self, dict_mod3):
        md_split = self.md_split(dict_=dict_mod3)
        panels = []
        for i in range(self.split_divide_by):
            panels.append(Panel(md_split[i], 
                                expand=self.expand, padding=self.padding, width=self.width, height=self.height, title=self.title, border_style=self.border_style, title_align=self.title_align))
        
        return panels
    



class simplpromt():
    """Small prompt/status panel shown above the stats.

    Fixed during the OOP refactor:
    - ``clear`` was a broken decorator (missing self/staticmethod), now a real
      staticmethod decorator factory
    - ``os.get_terminal_size()`` crashed when stdout is not a terminal (pipes,
      CI); it now falls back to 80x24
    - ``add_to_main`` width math could go negative for long prompts
    """

    def __init__(self, custom_promt=None, Defaults=True, add_to_default_promt=None) -> None:
        username = os.getlogin()
        self.username = f'[blue]{username}[/]'

        self.control_panel = Panel
        self.instace = Panel

        current_path = os.getcwd()
        # format path
        current_path = current_path.replace('\\', '/')
        # remove drive letter (e.g. 'D:' on Windows)
        self.current_path = current_path[2:]

        self.osx = sys.platform
        self.osxversion = sys.version

        try:
            self.sizes = os.get_terminal_size()
        except OSError:
            # Not a real terminal (pipes/CI) - use a sane fallback
            self.sizes = os.terminal_size((80, 24))

        if custom_promt:
            self.custom_promt = custom_promt
        else:
            self.old_promt = f"[green]PyStats@[/]{self.username}: {self.current_path} "
            self.custom_promt = self.old_promt

        if add_to_default_promt:
            self.custom_promt += f' {add_to_default_promt}'

        if Defaults:
            print((self.instace(f"{self.custom_promt} \n[gray7]OS: {self.osx} {self.osxversion}[/] $",
                                height=4, border_style='grey39', box=rich.box.HORIZONTALS)))

    @staticmethod
    def clear():
        def cls(func):
            def wrapper(*args, **kwargs):
                os.system('cls' if os.name == 'nt' else 'clear')
                func(*args, **kwargs)
            return wrapper
        return cls

    @clear()
    def add_to_main(self, text, cls_previous=False):
        if cls_previous:
            self.custom_promt = self.old_promt
        self.custom_promt += f' {text}'
        width = max(self.sizes[0] - len(self.custom_promt) - 15, 20)
        print((self.instace(self.custom_promt, height=3, width=width,
                            border_style='grey39', box=rich.box.HORIZONTALS)))

    def update(self, text):
        print(f"  {text}")


class VisualWrapper():
    def __init__(self, directory=None, adhd_mode=False, extra_adhd=False,
                 config: 'PyStatsConfig' = None) -> None:
        self._config = config if config is not None else _get_default_config()

        self.directory = directory if directory is not None else self._config.working_path

        #Fix when self.directory has only 1 file
        if isinstance(self.directory, str):
            self.directory = [self.directory]

        self.f_height_glace = 0 # Naming really is hard

        self.stat = Stat(self.directory, config=self._config)

        # what about the adhd mode?
        self.adhd_mode = adhd_mode
        self.adhd_modev2 = extra_adhd
        self.full_width = 0

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
    
    @staticmethod
    def assign_full_height(values):
        #Get biggest value from values
        max_value = max(values)        
    
    def quick_stats(self):
        current_directory = os.getcwd()
        tree = Tree(f'[magenta b]:open_file_folder: {current_directory}[/] [spring_green4]({len(self.directory)} {"File" if len(self.directory) == 1 else "Files"})[/]',
                    guide_style='red')
        # guide_style changes the colour of the lines that go to the files

        if _utils.is_nested_list(self.directory):
            combined_directories = "\n".join(list(itertools.chain.from_iterable(self.directory)))
        elif isinstance(self.directory, list):
            combined_directories = "\n".join([f'{file_}' for file_ in self.directory])
        else:
            combined_directories = f'{self.directory}'
    
        #Sort combined_directories by file size
        combined_directories = combined_directories.split("\n") 
        combined_directories.sort(key=lambda x: os.path.getsize(x), reverse=True) #Sorts from biggest to smallest looks cleaner imo
        combined_directories = "\n".join(combined_directories) 

        for py_files in combined_directories.split("\n"):
            #print() OFC THIS IS THE LINE I LEAVE HERE BY MISTAKE TRYNA FIRGURE IT OUT OH MY GODDDDD
            tree.add(f'[gold1]{py_files}[/] 'f'[spring_green4]({round(os.path.getsize(py_files) / 1000, 2)} kB)[/]')
            
        removed_files = self._config.removed_files
        if len(removed_files) != 0:
            #tree.add(f"[bright_black]Removed Files:[/]")
            for file_ in removed_files:
                tree.add(f"[bright_black]{file_} ({round(os.path.getsize(file_) / 1000, 2)} kB)[/]")

        return Panel(tree, title="[magenta b]Files obtained[/]", style='bright_blue')

    def get_line_count(self, _height=None, give_height=False):
        color1, color2 = self.get_colors()
        line_count = self.stat.line_count()

        line_count_md = "\n".join([f"[{color2}]{key}[/]: [{color1}]{value}[/]"
                                   for key, value in line_count.items()])

        line_count_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", line_count_md)

        line_count_md = f"""{line_count_md}"""
        line_count_panel = Panel(renderable=line_count_md,
                                 title="[magenta b]Line Count[/]",
                                 title_align="center",
                                 border_style="bright_blue",
                                 height=_height)


        
        
        possible_height = (len(line_count_md.split("\n")))
        if give_height:
            return possible_height + 2
        
        return line_count_panel

    def dupelinefind(self, _height=None):
        dupes = self.stat.dupelinefind() 
        color1, color2 = self.get_colors()
        dupes_md = "\n".join([f"[{color2}]{key}[/]: [{color1}]{value}[/]"
                                for key, value in dupes.items()])

        func_panel = Panel(renderable=dupes_md,
                           title="[magenta b]Dupe Lines[/]",
                           title_align="center",
                           border_style="blue",
                           width=30,
                           height=_height)

        return func_panel

    def get_variable(self, _height=None, give_height=False, raw=False, get_overde=None):
        n_variables = len(self.directory) 
        if get_overde:
            n_variables = get_overde
        # if int(n_variables) > 10:
        #     n_variables = 1
        if self._config.args.vars:
            n_variables = int(self._config.args.vars)
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

        # height
        possible_height = (len(variables_md.split("\n")))


        variable_panel = Panel(renderable=variables_md,
                               title=f"[magenta b]{start}[/]",
                               title_align="center",
                               border_style="bright_blue",
                               height=_height)

        if give_height:
            return possible_height
        if raw:
            return variables

        return variable_panel        

    def var_combine(self):
        #get all matches between self.get_variable(raw=True, get_overde=999999) and self.stat.get_var_types()
        #then combine them into a dict
        #then return that dict
        var = self.get_variable(raw=True, get_overde=999999)
        var_type = self.stat.get_var_types()
        
        #find matches from both and its type
        matches = {}
        for key, value in var.items():
            for key2, value2 in var_type.items():
                if key == key2:
                    matches[key] = [value, value2]

        return matches
        
    def visual_var_combine(self, typecolor="bright_yellow", limit=None, back=True):
        all_var = self.var_combine()
        color1, color2 = self.get_colors()
        
        main_dict = {} 
        
        #make a panel out of it
        #then return that panel
        for key, value in all_var.items():
            newval = f"[{typecolor}]{value[1]}[/]"
            all_var[key] = value[0], newval
        var_md = "\n".join([f"[{color2}]{key}[/]: [{color1}]{value}[/]"
                                    for key, value in all_var.items()])
        #The type should be a different color
        
        var_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", var_md)
        old_md = var_md
        var_md = custom_panel(var_md).md_split(3)
        penl = []
        
        
        for smtn in var_md:
            var_panel = Panel(renderable=smtn,
                                    title=f"[magenta b]Variable types[/]",
                                    title_align="center",
                                    border_style="bright_blue",
                                    height=limit)
            penl.append(var_panel)

        
        if back:
            old_panel = Panel(renderable=old_md,
                                    title=f"[magenta b]Variable types[/]",
                                    title_align="center",
                                    border_style="bright_blue",
                                    height=limit)
            return old_panel
        return penl
    
    def visual_var_combinev2(self, typecolor="bright_yellow", limit=None):
        all_var = self.var_combine()
        color1, color2 = self.get_colors()
        
        main_dct = {}
        formatted = []
        
        for i in all_var.values():
            formatted.append(i[1])
            
        #if not in main_dct add it and if it is there add 1 to it
        for i in formatted:
            if i not in main_dct:
                main_dct[i] = 1
            else:
                main_dct[i] += 1
            
            
        #format it in order of bigger to smallest
        main_dct = {k: v for k, v in sorted(main_dct.items(), key=lambda item: item[1], reverse=True)}
        
        all_vars_md = "\n".join([f"[{color2}]{key}[/]: [{color1}]{value}[/]"
                                  for key, value in main_dct.items()])
        all_vars_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", all_vars_md)
        
        panel = Panel(renderable=all_vars_md,
                                    title=f"[black]Variable types[/]",
                                    title_align="center",
                                    border_style="bright_blue")
        
        return panel
        
        
        

        
    
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

        #remove ,
        classes_md = re.sub(r",", "\n", classes_md)

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
                    width = len(max(old_func, key=len)) - 5 #All this fixes are absolute trash tbh
                elif get_ == 2:
                    title = '[black]In File'
                    #iterate threw old_func, get the length of the longest string, and add 1
                    width = len(max(old_func, key=len)) + 4 #This takes the largest string and adds 4 to to get pixel perfect
                    #width = len(max(old_func)) + 4 #Need to fix this
                elif get_ == 3:
                    title = '[black]Line'
                    width = len(max(old_func)) + 7
                else:
                    title = '[black]Times Used'
                    width = len(max(old_func)) * 10
                func_panel = Panel(renderable=func,
                                   title=title,
                                   title_align="left",
                                   border_style="blue",
                                   width=width)
                self.full_width += width #the panel wrapper in get all uses this
                return func_panel
            except Exception as e:
                print(e)
                pass
                
        func_panel = Panel(renderable=func,
                           title="[bright_black b]Functions[/]",
                           title_align="center",
                           border_style="red")

        return func_panel

    def get_statements(self, _height=None, give_height=False):
        color1, color2 = self.get_colors()
        statements = self.stat.get_control_statements()
        statements_dict = {'If': statements[0],
                           'While': statements[1],
                           'For': statements[2],
                           'With': statements[3],
                           'Try': statements[4],
                           'Total defined variables': statements[5]}
        #if any of them are 0 remove it
        statements_dict = {k: v for k, v in statements_dict.items() if v != 0} # Copilot is the best, this line removes all values which are 0 from the dict
        
        #return Panel.fit(termcharts.doughnut(statements_dict, title='Statments', rich=True)) #Term charts 
        # again, I think we shouldn't have the Total defined variable

        statements_md = "\n".join([f"[{color2}]{key}[/]: [{color1}]{value}[/]"
                                   for key, value in statements_dict.items()])
        statements_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", statements_md)

        # height
        possible_height = len(statements_md.splitlines()) + 2
            
        statements_panel = Panel(renderable=statements_md,
                                 title="[magenta b]Statements[/]",
                                 title_align="center",
                                 border_style="bright_blue",
                                 height=_height)
        if give_height:
            return possible_height

        return statements_panel

    def get_deco(self, _height=None, give_height=False):
        color1, color2 = self.get_colors()
        decorators = self.stat.count_decorator()

        decorators_md = "\n".join([f"[{color2}]{key}[/]: [{color1}]{value}[/]"
                                   for key, value in decorators.items()])
        decorators_md = re.sub(r"(.*?): (\d+)", r"\1: [b]\2[/]", decorators_md)
        
        possible_height = len(decorators_md.splitlines())
        
        decorators_panel = Panel(renderable=decorators_md,
                                 title="[magenta b]Decorators[/]",
                                 title_align="center",
                                 border_style="bright_blue",
                                height=_height)
        
        if give_height:
            return possible_height

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

    def img_render(self, remove_check=False, force_show=True, clear_screen=False,
                   imgpath=None):
        """Render the current stats view to an SVG file.

        Old behaviour kept: remove_check=True with no path saves 'PyStats.svg',
        an -imgpath saves 'PyStats <name>.svg'. Fixes: the duplicated save
        block is gone, opening the file is no longer Windows-only
        (os.startfile), and the "no path" error is returned before wasting
        time rendering the whole dashboard.
        """
        def get_info():
            print(self.get_all())
            if clear_screen:
                self.clear_term()

        if imgpath is None:
            imgpath = self._config.args.imgpath if self._config is not None else None

        if imgpath is None and not remove_check:
            return False, ('[red]img render path not given - no image rendered \n'
                           'Use the option -imgpath to specify a path[/]')

        get_info()
        file_name = f'PyStats {imgpath}.svg' if imgpath else 'PyStats.svg'
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(console.export_svg())

        if force_show:
            self._open_file(file_name)

        return [True]

    @staticmethod
    def _open_file(path: str) -> None:
        """Open *path* with the default OS viewer (old code was Windows-only)."""
        if os_name == "nt":
            os.startfile(path)
        elif sys.platform == "darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}"')

    def get_all(self, gui=True):
        promt = simplpromt(add_to_default_promt=f'[red]PyStats - Python File Stats [/]- [black]Getting statistics on [/][green]{len(self.directory)}[/] [black]{"File" if len(self.directory) == 1 else "Files"}[/] $')
        total_time = 0
        for file in self.directory:
            #if file is small less than 5kb
            if os.path.getsize(file) < 5000:    
                total_time += 2 
            elif os.path.getsize(file) < 10000:
                total_time += 4
            elif os.path.getsize(file) < 20000:
                total_time += 5
            elif os.path.getsize(file) < 30000:
                total_time += 6
            elif os.path.getsize(file) < 100000:
                total_time += 10 
        promt.update(f'[black]This wont take longer then [green]{total_time}[/] seconds[/]')        
        
        
        imp_count = self.get_import_count()
        
        g1_height_max = (max(self.get_line_count(give_height=True), self.get_variable(give_height=True), self.get_statements(give_height=True), self.get_deco(give_height=True))) #max height of the first group to look better
        
        group1 = Columns([self.get_line_count(g1_height_max), self.get_variable(g1_height_max), self.get_statements(g1_height_max), self.dupelinefind(g1_height_max),
                            self.get_deco(g1_height_max)]) #self.reformat_args() to get args to debug

        group2 = Columns([imp_count[0], imp_count[1]], padding=(0, 1))

        group3 = Columns([self.get_func(1), self.get_func(4), self.get_func(3),
                            self.get_func(2), self.visual_var_combinev2()])  # v1 shows all and how many times each thing is called while v2 shows a summary of it v2 looks cleaner
        

        groups = Group(Columns([self.quick_stats(), self.reformat_args()], padding=(1, max(promt.sizes[0] - 130, 0))),# This exact number is needed for pixel perfect accuracy
                        Rule('[bright_black b]At a glance[/]', style='red'),
                        group1, self.get_class(),
                        Rule('[bright_black b]Functions & Classes[/]', style='red'), group3, #To remove the box around Functions & Classes remove panel wrapper, Panel(group3, style=self.get_colors()[0], width=self.full_width+7)
                        Rule('[bright_black b]Imports (from count is not working currently)',
                            style='red'), group2)
        if gui:
            return Panel(renderable=groups,
                            title="[bright_black b]All Stats[/]",
                            title_align="center", style='red', box=rich.box.HEAVY)


# ---------------------------------------------------------------------------
# Default config + legacy module-level names
#
# ``PyStats.py`` (the wrapper) and any code written against the old module
# still expect ``_PyStats.args`` / ``_PyStats.working_path`` /
# ``_PyStats.removed_files`` to exist, so the shared config is created here.
# ---------------------------------------------------------------------------
_default_config = PyStatsConfig()
args = _default_config.args
working_path = _default_config.working_path
removed_files = _default_config.removed_files

CustomPanel = custom_panel
SimplePrompt = simplpromt


def _get_default_config() -> PyStatsConfig:
    """Return the shared default config used by Stat and VisualWrapper."""
    return _default_config


def ensure_admin() -> None:
    """Re-launch the current process with admin privileges on Windows."""
    _default_config.ensure_admin()


if __name__ == '__main__':
    print('[red]PyStats is a python module that allows you to easily view your python statistics, '
          'Your getting all this info because your running this file directly, you should use the '
          'PyStats wrapper instead and use it in other python files[/]')
    print('[yellow]Looking for PyStats.py wrapper in the current directory[/]')
    if find('PyStats.py', '.'):
        print('[green]Found PyStats.py wrapper in the current directory, importing it[/]')
        os.system('Python PyStats.py')
    else:
        print('[red]Could not find PyStats.py wrapper in the working directory, '
              'Please install fully instead[/]')
        sys.exit(1)
