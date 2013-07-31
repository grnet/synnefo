#!/usr/bin/env python

"""
Setup slave server
"""

from utils import SynnefoCI


def setup_slave():
    """Setup slave server"""
    synnefo_ci = SynnefoCI(cleanup_config=True)
    # Build slave server
    synnefo_ci.create_server()
    # Copy synnefo repo to server
    synnefo_ci.clone_repo()


if __name__ == "__main__":
    setup_slave()
