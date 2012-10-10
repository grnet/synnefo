from kkconfig import QHTestCase
from kkconfig import new_quota_holder_client

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
            get_limits = [policy]
        )

        self.assertTrue(len(limits) > 1)