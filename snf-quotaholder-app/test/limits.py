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

from config import QHTestCase
from config import run_test_case
from config import printf
from config import rand_string
from random import randint

from synnefo.lib.quotaholder.api import InvalidDataError

class Data:
    def __init__(self, parent, **kwd):
        self.context  = kwd.get('context', parent.context)
        self.policy   = kwd.get('policy', parent.policy)
        self.capacity = kwd.get('capacity', parent.capacity)
        self.quantity = kwd.get('quantity', parent.quantity)
        self.import_limit = kwd.get('import_limit', parent.import_limit)
        self.export_limit = kwd.get('export_limit', parent.export_limit)
        # set_limits_has_rejected indicates whether the test expects a non-empty rejected list
        # after calling set_limits
        self.set_limits_has_rejected = kwd.get('set_limits_has_rejected', False)
        # get_limits_expected_length indicates the exact length of the limits list
        # returned by get_limits
        self.get_limits_expected_length = kwd.get('get_limits_expected_length', 1)

class LimitsTest(QHTestCase):
    context = {}
    policy = rand_string()
    capacity1 = 0
    capacity2 = 100
    capacity = capacity1
    quantity1 = capacity2
    quantity2 = capacity1
    quantity = quantity1
    import_limit_empty = 0
    import_limit_full_capacity = capacity
    import_limit_half_capacity = capacity / 2
    import_limit = import_limit_half_capacity
    export_limit_empty = 0
    export_limit_full_capacity = capacity
    export_limit_half_capacity = capacity / 2
    export_limit = export_limit_half_capacity

    def helper_set_limits(self, **kwd):
        """
        Calls set_limits and returns the rejected list (from the original API).
        """
        data = Data(self, **kwd)
        rejected = self.qh.set_limits(
            context = data.context,
            set_limits = [
                (data.policy,
                 data.quantity,
                 data.capacity,
                 data.import_limit,
                 data.export_limit)
            ]
        )

        if data.set_limits_has_rejected:
            self.assertTrue(len(rejected) > 1)
        else:
            self.assertTrue(len(rejected) == 0)

        return rejected

    def helper_get_limits(self, **kwd):
        """
        Calls get_limits and returns the limits list (from the original API)..
        """
        data = Data(self, **kwd)
        limits = self.qh.get_limits(
            context = data.context,
            get_limits = [data.policy]
        )

        self.assertEqual(len(limits), data.get_limits_expected_length)

        return limits

    def test_010_set_get(self):
        """
        quantity = 0, capacity = 100
        """
        self.helper_set_limits(quantity = 0, capacity = 100, should_have_rejected = False)
        self.helper_get_limits(get_limits_expected_length = 1)

    def test_011_set_get(self):
        """
        quantity = 100, capacity = 0
        """
        self.helper_set_limits(quantity = 100, capacity = 0, should_have_rejected = False)
        self.helper_get_limits(get_limits_expected_length = 1)

    def test_020_set_get_empty_policy_name(self):
        """
        Tests empty policy name
        """
        with self.assertRaises(InvalidDataError):
            self.helper_set_limits(policy = '', set_limits_has_rejected = False)
            self.helper_get_limits(policy = '', get_limits_expected_length = 1)


if __name__ == "__main__":
    import sys
    printf("Using {0}", sys.executable)
    run_test_case(LimitsTest)
