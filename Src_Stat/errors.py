"""Created on Aug 17 00:17:59 2022."""


class PyStatsError(Exception):
    pass


class OutputNotSpecified(PyStatsError):
    pass


class NoFilePresent(PyStatsError):
    pass