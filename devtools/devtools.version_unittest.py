#!/usr/bin/env python
#
# Copyright 2012 GRNET S.A. All rights reserved.
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
#
#

"""Unit Tests for devtools.version

Provides unit tests for module devtools.version,
for automatic generation of version strings.

"""

import os
import unittest
from pkg_resources import parse_version
from version import debian_version_from_python_version


class DebianVersionObject(object):
    """Object representing a Debian Version."""
    def __init__(self, pyver):
        self.version = debian_version_from_python_version(pyver)

    def __str__(self):
        return self.version


def debian_compare_versions(a, op, b):
    i = os.system("dpkg --compare-versions %s %s %s" % (a, op, b))
    return i == 0

# Set ordering between DebianVersionObject objects, by adding
# debian_compare_versions
for op in ["lt", "le", "eq", "ne", "gt", "ge"]:
    def gen(op):
        def operator_func(self, other):
            return debian_compare_versions(self.version, op, other.version)
        return operator_func
    setattr(DebianVersionObject, "__%s__" % op, gen(op))


def _random_commit():
    import random
    import string
    return "".join(random.choice(string.hexdigits) for n in xrange(8)).lower()


# Add a random commit number at the end of snapshot versions
def version_with_commit(parse_func, v):
    if "_" in v:
        return parse_func(v + "_" + _random_commit())
    else:
        return parse_func(v)

V = lambda v: version_with_commit(parse_version, v)
D = lambda v: version_with_commit(DebianVersionObject, v)


class TestVersionFunctions(unittest.TestCase):
    def setUp(self):
        self.version_orderings = (
            ("0.14next", ">", "0.14"),
            ("0.14next", ">", "0.14rc7"),
            ("0.14next", "<", "0.14.1"),
            ("0.14rc6", "<", "0.14"),
            ("0.14.2rc6", ">", "0.14.1"),
            ("0.14next_150", "<", "0.14next"),
            ("0.14.1next_150", "<", "0.14.1next"),
            ("0.14.1_149", "<", "0.14.1"),
            ("0.14.1_149", "<", "0.14.1_150"),
            ("0.13next_102", "<", "0.13next"),
            ("0.13next", "<", "0.14rc5_120"),
            ("0.14rc3_120", "<", "0.14rc3"),
            # The following test fails, but version.python_version
            # will never try to produce such a version:
            # ("0.14rc3", "<", "0.14_1"),
            ("0.14_120", "<", "0.14"),
            ("0.14", "<", "0.14next_20"),
            ("0.14next_20", "<", "0.14next"),
        )

    def test_python_versions(self):
        for a, op, b in self.version_orderings:
            res = compare(V, a, op, b)
            self.assertTrue(res, "Python version: %s %s %s"
                                 " is not True" % (a, op, b))

    def test_debian_versions(self):
        for a, op, b in self.version_orderings:
            res = compare(D, a, op, b)
            self.assertTrue(res, "Debian version %s %s %s"
                                 " is not True" % (a, op, b))


def compare(function, a, op, b):
    import operator
    str_to_op = {"<": operator.lt,
            "<=": operator.le,
            "==": operator.eq,
            ">": operator.gt,
            ">=": operator.ge}
    try:
        return str_to_op[op](function(a), function(b))
    except KeyError:
        raise ValueError("Unknown operator '%s'" % op)

if __name__ == '__main__':
    unittest.main()
