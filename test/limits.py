from kkconfig import QHTestCase
from kkconfig import run_test_case

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
            get_limits = [(policy, )] # or is it just policy, i.e. no
        )

        self.assertTrue(len(limits) > 1)

if __name__ == "__main__":
    run_test_case(LimitsTest)