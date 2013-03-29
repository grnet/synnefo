# Copyright 2012 - 2013 GRNET S.A. All rights reserved.
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

import json
import csv
import functools
from datetime import datetime
from django.utils.timesince import timesince, timeuntil

from synnefo.util.text import uenc, udec


def parse_bool(value, strict=True):
    """Convert a string to boolen value.

    If string is True, then ValueError will be raised, if the string can not be
    converted to boolean. Otherwise the string will be returned as is.

    """
    if value.lower() in ("yes", "true", "t", "1"):
        return True
    if value.lower() in ("no", "false", "f", "0"):
        return False

    if strict:
        raise ValueError("Can convert '%s' to boolean value")
    else:
        return value


def format_bool(b):
    """Convert a boolean value to YES or NO."""
    return "YES" if b else "NO"


def format_date(d):
    if not d:
        return ""

    if d < datetime.now():
        return timesince(d) + " ago"
    else:
        return "in " + timeuntil(d)


def parse_filters(filter_by):
    """Parse a string into lookup parameters for QuerySet.filter(**kwargs).

    This functions converts a string of comma-separated key 'cond' val triples
    to two dictionaries, containing lookup parameters to be used for filter
    and exclude functions of QuerySet.

    e.g. filter_by="foo>=2, baz!=4" -> ({"foo__gte": "2"}, {"baz": "4"})

    """

    filter_dict = {}
    exclude_dict = {}

    filter_list = filter_by.split(",")

    def map_field_type(query):
        if "!=" in query:
            key, val = query.split("!=")
            exclude_dict[key] = parse_bool(val, strict=False)
            return

        OP_MAP = {
            ">=": "__gte",
            "=>": "__gte",
            ">":  "__gt",
            "<=": "__lte",
            "=<": "__lte",
            "<":  "__lt",
            "=":  "",
        }

        for op, new_op in OP_MAP.items():
            if op in query:
                key, val = query.split(op)
                filter_dict[key + new_op] = parse_bool(val, strict=False)
                return

    map(lambda x: map_field_type(x), filter_list)

    return (filter_dict, exclude_dict)


def pprint_table(out, table, headers=None, output_format='pretty',
                 separator=None):
    """Print a pretty, aligned string representation of table.

    Works by finding out the max width of each column and padding to data
    to this value.
    """

    assert(isinstance(table, (list, tuple))), "Invalid table type"
    if headers:
        assert(isinstance(headers, (list, tuple))), "Invalid headers type"

    sep = separator if separator else "  "

    def stringnify(obj):
        if isinstance(obj, (unicode, str)):
            return udec(obj)
        else:
            return str(obj)

    if headers:
        headers = map(stringnify, headers)
    table = [map(stringnify, row) for row in table]

    if output_format == "json":
        assert(headers is not None), "json output format requires headers"
        table = [dict(zip(headers, row)) for row in table]
        out.write(json.dumps(table, indent=4))
        out.write("\n")
    elif output_format == "csv":
        cw = csv.writer(out)
        if headers:
            table.insert(0, headers)
        table = map(functools.partial(map, uenc), table)
        cw.writerows(table)
    elif output_format == "pretty":
        # Find out the max width of each column
        columns = [headers] + table if headers else table
        widths = [max(map(len, col)) for col in zip(*(columns))]

        t_length = sum(widths) + len(sep) * (len(widths) - 1)
        if headers:
            # pretty print the headers
            line = sep.join(uenc(v.rjust(w)) for v, w in zip(headers, widths))
            out.write(line + "\n")
            out.write("-" * t_length + "\n")

        # print the rest table
        for row in table:
            line = sep.join(uenc(v.rjust(w)) for v, w in zip(row, widths))
            out.write(line + "\n")
    else:
        raise ValueError("Unknown output format '%s'" % output_format)
