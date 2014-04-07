# Copyright 2013-2014 GRNET S.A. All rights reserved.
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

from synnefo.util import units
from snf_django.management.commands import CommandError
from django.db.models import Q


OP_MAP = [
    ("!=", lambda x: ~x, ""),
    (">=", lambda x: x, "__gte"),
    ("=>", lambda x: x, "__gte"),
    (">", lambda x: x, "__gt"),
    ("<=", lambda x: x, "__lte"),
    ("=<", lambda x: x, "__lte"),
    ("<", lambda x: x, "__lt"),
    ("=", lambda x: x, ""),
    ]


def parse_filter(exp):
    for s, prepend, op in OP_MAP:
        key, sep, value = exp.partition(s)
        if s == sep:
            return key, prepend, op, value
    raise CommandError("Could not parse filter.")


def make_query(flt, handlers):
    key, prepend, opstr, value = parse_filter(flt)
    try:
        (dbkey, parse) = handlers[key]
        return prepend(Q(**{dbkey+opstr: parse(value)}))
    except KeyError:
        return None


def parse_with_unit(value):
    try:
        return units.parse(value)
    except units.ParseError:
        raise CommandError("Failed to parse value, should be an integer, "
                           "possibly followed by a unit, or 'inf'.")
