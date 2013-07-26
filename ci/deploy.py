#!/usr/bin/env python

"""
Deploy Synnefo using snf-deploy
"""

from utils import SynnefoCI


def deploy_synnefo():
    """Deploy Synnefo using snf-deploy"""
    synnefo_ci = SynnefoCI()
    synnefo_ci.deploy_synnefo()


if __name__ == "__main__":
    deploy_synnefo()
