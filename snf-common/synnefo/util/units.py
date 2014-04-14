# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from synnefo.lib.ordereddict import OrderedDict
import re

PRACTICALLY_INFINITE = 2**63 - 1
DEFAULT_PARSE_BASE = 1024
PARSE_EXPONENTS = {
    '':      0,
    'bytes': 0,
    'K':     1,
    'KB':    1,
    'KIB':   1,
    'M':     2,
    'MB':    2,
    'MIB':   2,
    'G':     3,
    'GB':    3,
    'GIB':   3,
    'T':     4,
    'TB':    4,
    'TIB':   4,
    'P':     5,
    'PB':    5,
    'PIB':   5,
}

_MATCHER = re.compile('^(\d+\.?\d*)(.*)$')


class ParseError(Exception):
    pass


def _parse_number_with_unit(s):
    match = _MATCHER.match(s)
    if not match:
        raise ParseError()
    number, unit = match.groups()
    try:
        number = long(number)
    except ValueError:
        number = float(number)

    return number, unit.strip().upper()


def parse_with_style(s):
    if isinstance(s, (int, long)):
        return s, 0

    if s in ['inf', 'infinite']:
        return PRACTICALLY_INFINITE, 0

    n, unit = _parse_number_with_unit(s)
    try:
        exponent = PARSE_EXPONENTS[unit]
    except KeyError:
        raise ParseError()
    multiplier = DEFAULT_PARSE_BASE ** exponent
    return long(n * multiplier), exponent


def parse(s):
    n, _ = parse_with_style(s)
    return n


UNITS = {
    'bytes': {
        'DISPLAY': ['bytes', 'kB', 'MB', 'GB', 'TB', 'PB'],
        'BASE': 1024,
    }
}

STYLE_TO_EXP = OrderedDict(
    [('b',  0),
     ('kb', 1),
     ('mb', 2),
     ('gb', 3),
     ('tb', 4),
     ('pb', 5),
     ]
)

STYLES = STYLE_TO_EXP.keys() + ['auto', 'none']


class StyleError(Exception):
    pass


def show_float(n):
    if n < 1:
        return "%.3f" % n
    if n < 10:
        return "%.2f" % n
    return "%.1f" % n


def get_exponent(style):
    if isinstance(style, (int, long)):
        if style in STYLE_TO_EXP.values():
            return style
        else:
            raise StyleError()
    else:
        try:
            return STYLE_TO_EXP[style]
        except KeyError:
            raise StyleError()


def show(n, unit, style=None):
    if style == 'none':
        return str(n)

    if n == PRACTICALLY_INFINITE:
        return 'inf'

    try:
        unit_dict = UNITS[unit]
    except KeyError:
        return str(n)

    BASE = unit_dict['BASE']
    DISPLAY = unit_dict['DISPLAY']

    if style is None or style == 'auto':
        if n < BASE:
            return "%d %s" % (n, DISPLAY[0])
        n = float(n)
        for i in DISPLAY[1:]:
            n = n / BASE
            if n < BASE:
                break
        return "%s %s" % (show_float(n), i)

    exponent = get_exponent(style)
    unit_display = DISPLAY[exponent]
    if exponent == 0:
        return "%d %s" % (n, unit_display)

    divisor = BASE ** exponent
    n = float(n)
    n = n / divisor
    return "%s %s" % (show_float(n), unit_display)
