# Copyright 2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

from synnefo.lib.ordereddict import OrderedDict
import re

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
    try:
        unit_dict = UNITS[unit]
    except KeyError:
        return str(n)

    if style == 'none':
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
