from config import QHTestCase
from config import run_test_case
from config import printf

class LimitsTest(QHTestCase):
    def test_01_set_get(self):
        policy = 'Some policy'
        quantity = 0
        capacity = 100
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

    def test_02_set_get_empty_policy_name(self):
        """
        Tests empty policy name
        """
        policy = ''
        quantity = 0
        capacity = 100
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