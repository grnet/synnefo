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

import json
import operator
import locale
import unicodedata

from datetime import datetime
from django.utils.timesince import timesince, timeuntil
from django.db.models.query import QuerySet
from django.utils.encoding import smart_unicode, smart_str
from snf_django.management.unicodecsv import UnicodeWriter


def smart_locale_unicode(s, **kwargs):
    """Wrapper around 'smart_unicode' using user's preferred encoding."""
    encoding = locale.getpreferredencoding()
    return smart_unicode(s, encoding=encoding, **kwargs)


def smart_locale_str(s, errors='replace', **kwargs):
    """Wrapper around 'smart_str' using user's preferred encoding."""
    encoding = locale.getpreferredencoding()
    return smart_str(s, encoding=encoding, errors=errors, **kwargs)


def safe_string(s):
    """Escape control characters from unicode and string objects."""
    if not isinstance(s, basestring):
        return s
    if isinstance(s, unicode):
        return "".join(ch.encode("unicode_escape")
                       if unicodedata.category(ch)[0] == "C" else
                       ch for ch in s)
    return s.encode("string_escape")


def parse_bool(value, strict=True):
    """Convert a string to boolen value.

    If strict is True, then ValueError will be raised, if the string can not be
    converted to boolean. Otherwise the string will be returned as is.

    """
    if isinstance(value, bool):
        return value

    if value.lower() in ("yes", "true", "t", "1"):
        return True
    if value.lower() in ("no", "false", "f", "0"):
        return False

    if strict:
        raise ValueError("Cannot convert '%s' to boolean value" % value)
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


def filter_results(results, filters):
    if isinstance(results, QuerySet):
        return filter_queryset_results(results, filters)
    elif isinstance(results, list):
        return filter_object_results(results, filters)
    else:
        raise ValueError("Invalid type for results argument: %s", results)


def parse_queryset_filters(filters):
    """Parse a string into lookup parameters for QuerySet.filter(**kwargs).

    This functions converts a string of comma-separated key 'cond' val triples
    to two dictionaries, containing lookup parameters to be used for filter
    and exclude functions of QuerySet.

    e.g. filter_by="foo>=2, baz!=4" -> ({"foo__gte": "2"}, {"baz": "4"})

    """
    OP_MAP = [
        (">=", "__gte"),
        ("=>", "__gte"),
        (">",  "__gt"),
        ("<=", "__lte"),
        ("=<", "__lte"),
        ("<", "__lt"),
        ("=", ""),
        ]

    filter_dict = {}
    exclude_dict = {}
    for filter_str in filters.split(","):
        if "!=" in filter_str:
            key, val = filter_str.split("!=")
            exclude_dict[key] = parse_bool(val, strict=False)
            continue
        for op, new_op in OP_MAP:
            if op in filter_str:
                key, val = filter_str.split(op)
                filter_dict[key + new_op] = parse_bool(val, strict=False)
                break
        else:
            raise ValueError("Unknown filter expression: %s" % filter_str)

    return (filter_dict, exclude_dict)


def filter_queryset_results(results, filters):
    filter_dict, exclude_dict = parse_queryset_filters(filters)
    return results.exclude(**exclude_dict).filter(**filter_dict)


def parse_object_filters(filters):
    OP_MAP = [
        (">=", operator.ge),
        ("=>", operator.ge),
        (">",  operator.gt),
        ("<=", operator.le),
        ("=<", operator.le),
        ("<", operator.lt),
        ("!=", operator.ne),
        ("=", operator.eq),
    ]
    filters = []
    for filter_str in filters.split(","):
        for op, op_func in OP_MAP:
            if op in filter_str:
                key, val = filter_str.split(op)
                filters.append((key.strip(), op_func, val.strip()))
                break
        else:
            raise ValueError("Unknown filter expression: %s" % filter_str)
    return filters


def filter_object_results(results, filters):
    results = list(results)
    if results is []:
        return results
    zero_result = results[0]
    for key, op_func, val in parse_object_filters(filters):
        val_type = type(getattr(zero_result, key))
        results = filter(lambda x: op_func(getattr(x, key), val_type(val)),
                         results)
    return results


def print_title(out, title, t_length):
    if title is not None:
        t_length = max(t_length, len(title))
        out.write("-" * t_length + "\n")
        out.write(title.center(t_length) + "\n")
        out.write("-" * t_length + "\n")


def pprint_table(out, table, headers=None, output_format='pretty',
                 separator=None, vertical=False, title=None):
    """Print a pretty, aligned string representation of table.

    Works by finding out the max width of each column and padding to data
    to this value.
    """

    assert(isinstance(table, (list, tuple))), "Invalid table type"
    if headers:
        assert(isinstance(headers, (list, tuple))), "Invalid headers type"

    sep = separator if separator else "  "

    if headers:
        headers = map(smart_unicode, headers)
    table = [map(smart_unicode, row) for row in table]

    if output_format == "json":
        assert(headers is not None), "json output format requires headers"
        table = [dict(zip(headers, row)) for row in table]
        out.write(json.dumps(table, indent=4))
        out.write("\n")
    elif output_format == "csv":
        enc = locale.getpreferredencoding()
        cw = UnicodeWriter(out, encoding=enc)
        if headers:
            table.insert(0, headers)
        cw.writerows(table)
    elif output_format == "pretty":
        if vertical:
            row = table[0]
            max_key = max(map(len, headers))
            max_val = max(map(len, row))
            t_length = max_key + len(sep) + max_val
            print_title(out, title, t_length)
            assert(len(table) == 1)
            for row in table:
                for (k, v) in zip(headers, row):
                    k = k.ljust(max_key)
                    out.write("%s: %s\n" % (k, v))
        else:
            # Find out the max width of each column
            columns = [headers] + table if headers else table
            widths = [max(map(len, col)) for col in zip(*(columns))]

            t_length = sum(widths) + len(sep) * (len(widths) - 1)
            print_title(out, title, t_length)
            if headers:
                # pretty print the headers
                line = sep.join(v.rjust(w)
                                for v, w in zip(headers, widths))
                out.write(line + "\n")
                out.write("-" * t_length + "\n")

            # print the rest table
            for row in table:
                line = sep.join(v.rjust(w) for v, w in zip(row, widths))
                out.write(line + "\n")
    else:
        raise ValueError("Unknown output format '%s'" % output_format)
