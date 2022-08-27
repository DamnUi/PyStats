"""Created on Jul 28 00:24:59 2022."""

import ctypes
import re
from collections import Counter


def is_nested_list(input_list):
    return any(isinstance(x, list) for x in input_list)


def list_to_counter_dictionary(list_):
    return dict(Counter(list_))


def from_imports(input_file, get_assets=False):
    try:
        result = []
        with open(input_file, encoding='utf8') as input_file:
            for _code_line in input_file:
                if re.match(r"^from\s\w+(?:.\w+)?\simport\s\w+(?:,\s\w+)*", _code_line):
                    result.append(_code_line.strip())

        if not get_assets:
            result = [_code_line.split(' import ')[0].strip() for _code_line in result]
        else:
            assets = []
            for _code_line in result:
                _code_line = _code_line.split(' import ')[1]
                if _code_line.count(',') > 1:
                    assets.extend([i.split('as')[0].strip()
                                   if 'as' in i else i.strip()
                                   for i in _code_line.split(', ')])
                else:
                    assets.extend([i.split(' as ')[0] if 'as' in i else i
                                   for i in _code_line.split(', ')])

            result = [_code_line.split(' import ')[0].strip() for _code_line in result]

            result, assets = zip(*sorted(zip(result, assets)))

            result_ = {key: [] for key in result}
            for res_, ast_ in zip(result, assets):
                result_[res_].extend([x.strip() for x in ast_.split(',')])

            # change the key 'from' to 'from .' for the base directory imports
            result = {'from .' if key == 'from' else key: value for key, value in result_.items()}
    except ValueError:
        result = {}

    return result


def import_imports(input_file):
    import_ = []
    with open(input_file, encoding='utf8') as input_file:
        for _code_line in input_file:
            if re.match(r"^import\s\w+", _code_line):
                import_.append(_code_line.strip())

    return dict(Counter(import_))


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except AttributeError:
        return False


class TabularView:

    def __init__(self, function_names, file_name, line_no, occurrence):
        self.function_names = function_names
        self.file_name = file_name
        self.line_no = line_no
        self.occurrence = occurrence

        self.out = ''

    @staticmethod
    def __color_border(input_string, color='magenta'):
        return f'[{color}]{input_string}[/]'

    def __equalize_line_numbers(self):
        # taken from comment by MoTSCHIGGE under https://stackoverflow.com/a/26446766/3212945
        self.line_no = [f'{line_no:4d}' for line_no in self.line_no]
        self.occurrence = [f'{occurrence:3d}' for occurrence in self.occurrence]

    def make_table(self, border_color='magenta'):
        self.__equalize_line_numbers()
        # determine the max width of file path
        max_file_name = max([len(x) for x in self.file_name]) + 4
        max_func_name = max([len(x) for x in self.function_names]) + 4

        bold_red, bright_green, bright_blue, bright_black, magenta = 10, 17, 16, 17, 12

        line_ = f"{self.__color_border('-', color=border_color)}" * (max_func_name + max_file_name
                                                                     + 18 + 24)
        _ = f"{self.__color_border('|', color=border_color)}"
        self.out = line_ + '\n'
        self.out += '[red b]Function Name[/]'.center(max_func_name + bold_red) + f'{_}'
        self.out += '[red b]File Name[/]'.center(max_file_name + bold_red + 2) + f'{_}'
        self.out += '[red b]def @ line #[/]'.center(18 + bold_red) + f'{_}'
        self.out += '[red b]Occurrences[/]'.center(20 + bold_red) + '\n'
        self.out += line_ + '\n'
        self.out += '\n'.join(
                [f'[bright_green]{h}[/]'.ljust(max_func_name + bright_green) + f'{_}' +
                 f'[bright_blue]  {i}[/]'.ljust(max_file_name + bright_blue + 2) +
                 f'{_}' +
                 f'[bright_black]{j}[/]'.center(18 + bright_black) + f'{_}' +
                 f'{k if int(k) > 0 else "[red]defined only[/]"}'.center([20 if int(k) > 0
                                                                          else 28][0])
                 for h, i, j, k in zip(self.function_names, self.file_name,
                                       self.line_no, self.occurrence)]
                )

        return self.out
