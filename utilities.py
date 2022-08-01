"""Created on Jul 28 00:24:59 2022."""

from collections import Counter


def AND(cond1, cond2):
    return cond1 and cond2


def OR(cond1, cond2):
    return cond1 or cond2


def from_imports(input_file, get_assets=False):
    try:
        result = []
        with open(input_file, encoding='utf8') as input_file:
            for _code_line in input_file:
                if OR(_code_line.startswith('from'), OR(_code_line.startswith('    from'),
                                                        _code_line.startswith('  from'))):
                    _code_line = _code_line.replace('from .', 'from ')
                    result.append(_code_line)

        if not get_assets:
            result_ = [x.split('as')[0].strip() for x in result]
        else:
            assets = [_code_line.split('import')[1].split('as')[0].strip() for _code_line in result]
            result = [_code_line.split('import')[0].strip() for _code_line in result]

            result, assets = zip(*sorted(zip(result, assets)))

            result_ = {key: [] for key in result}
            for res_, ast_ in zip(result, assets):
                result_[res_].extend([x.strip() for x in ast_.split(',')])

        # change the key 'from' to 'from .' for the base directory imports
        result_ = {'from .' if key == 'from' else key: value for key, value in result_.items()}
        result = result_
    except ValueError:
        result = dict()

    return result


def import_imports(input_file):
    import_ = []
    with open(input_file, encoding='utf8') as input_file:
        for _code_line in input_file:
            _code_line = _code_line.strip()
            if AND('import' in _code_line, 'from' not in _code_line):
                _code_line = _code_line.split('as')[0]
                import_.append(_code_line.strip())

    return dict(Counter(import_))
