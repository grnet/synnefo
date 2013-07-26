#!/usr/bin/env python

"""
Build Synnefo packages for debian
"""

from utils import SynnefoCI


def autopkg_debian():
    """Build synnefo packages for debian"""
    synnefo_ci = SynnefoCI()
    synnefo_ci.build_synnefo()


if __name__ == "__main__":
    autopkg_debian()
