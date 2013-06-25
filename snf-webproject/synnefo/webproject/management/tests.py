import sys
from synnefo.webproject.management import utils

# Use backported unittest functionality if Python < 2.7
try:
    import unittest2 as unittest
except ImportError:
    if sys.version_info < (2, 7):
        raise Exception("The unittest2 package is required for Python < 2.7")
    import unittest


class ParseFiltersTestCase(unittest.TestCase):
    def test_parse_empty(self):
        res = utils.parse_filters("")
        self.assertEqual(res, ({}, {}))

    def test_parse_one(self):
        res = utils.parse_filters("x=2")
        self.assertEqual(res, ({"x": "2"}, {}))
        res = utils.parse_filters("x!=2")
        self.assertEqual(res, ({}, {"x": "2"}))

    def test_parse_many(self):
        res = utils.parse_filters("x=2,x>=3,y!=4,z<3")
        filters = {"x": "2", "x__gte": "3", "z__lt": "3"}
        excludes = {"y": "4"}
        self.assertEqual(res, (filters, excludes))

if __name__ == '__main__':
    unittest.main()
