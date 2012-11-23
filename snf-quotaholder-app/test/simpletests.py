from config import QHTestCase
from config import run_test_case
from config import rand_string
from config import printf

from commissioning import CallError

class QHAPITest(QHTestCase):

    def test_001(self):
        r = self.qh.list_entities(entity='system', key='')
        self.assertEqual(r, ['system'])

    def test_002(self):
        with self.assertRaises(CallError):
            self.qh.list_entities(entity='systems', key='')


if __name__ == "__main__":
    import sys
    printf("Using {0}", sys.executable)
    run_test_case(QHAPITest)
