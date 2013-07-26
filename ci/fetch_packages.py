#!/usr/bin/env python

"""
Download Synnefo packages
"""

from utils import SynnefoCI


def fetch_packages():
    """Download Synnefo packages"""
    synnefo_ci = SynnefoCI()
    synnefo_ci.fetch_packages()


if __name__ == "__main__":
    fetch_packages()
