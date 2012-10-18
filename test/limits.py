from config import QHTestCase
from config import run_test_case
from config import printf
from config import rand_string
from random import randint

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
    capacity = randint(10, 1000)
    quantity_empty = 0
    quantity_half_capacity = capacity / 2
    quantity_twice_capacity = capacity * 2
    quantity = quantity_half_capacity
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

    def test_01_set_get(self):
        self.helper_set_limits(should_have_rejected = False)
        self.helper_get_limits(get_limits_expected_length = 1)


    def test_02_set_get_empty_policy_name(self):
        """
        Tests empty policy name
        """
        self.helper_set_limits(policy = '', set_limits_has_rejected = False)
        self.helper_get_limits(policy='', get_limits_expected_length = 1)

    def test_02_set_get_bad_quantity(self):
        """
        Test quantity that exceeds capacity.
        QUESTION: Should this fail?
        """
        policy = ''
        capacity = 100
        quantity = capacity * 2
        importLimit = 10
        exportLimit = 10

        # SET
        rejected = self.qh.set_limits(
            context = {},
            set_limits = [
                (policy, quantity, capacity, importLimit, exportLimit)
            ]
        )

        self.assertEqual([], rejected)

        # GET
        limits = self.qh.get_limits(
            context = {},
            get_limits = [policy] # or is it just policy, i.e. no
        )

        self.assertTrue(len(limits) == 1)


if __name__ == "__main__":
    import sys
    printf("Using {0}", sys.executable)
    run_test_case(LimitsTest)
