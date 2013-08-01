#!/usr/bin/env python

"""
Run burnin functional test suite
"""

from utils import SynnefoCI


def run_burnin():
    """Run burnin functional test suite"""
    synnefo_ci = SynnefoCI()
    synnefo_ci.run_burnin()


if __name__ == "__main__":
    run_burnin()
