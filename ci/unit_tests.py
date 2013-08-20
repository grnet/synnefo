#!/usr/bin/env python

"""
Run Synnefo unit test suite
"""

from utils import SynnefoCI


def unit_test():
    """Run Synnefo unit test suite"""
    synnefo_ci = SynnefoCI()
    synnefo_ci.unit_test()


if __name__ == "__main__":
    unit_test()
