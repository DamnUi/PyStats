"""Created on Jul 28 00:24:59 2022."""

import ctypes
import re
from collections import Counter



def is_nested_list(input_list):
    return any(isinstance(x, list) for x in input_list)


def AND(cond1, cond2):
    return cond1 and cond2


def OR(cond1, cond2):
    return cond1 or cond2


def list_to_counter_dictionary(list_):
    return dict(Counter(list_))


def from_imports(input_file, get_assets=False):
    try:
        result = []
        with open(input_file, encoding='utf8') as input_file:
            for _code_line in input_file:
                if re.match(r"^from\s\w+(?:.\w+)?\simport\s\w+(?:,\s\w+)*", _code_line):
                    _code_line = re.sub(r'#(?<=#).*', '', _code_line)
                    _code_line = re.sub(r'(?<=\s)as\s\w+', '', _code_line)
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
                _code_line = re.sub(r'#(?<=#).*', '', _code_line)
                _code_line = re.sub(r'(?<=\s)as\s\w+', '', _code_line)
                import_.append(_code_line.strip())

    return dict(Counter(import_))


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except AttributeError:
        return False
