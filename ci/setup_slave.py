#!/usr/bin/env python

"""
Setup slave server
"""

from utils import SynnefoCI


def setup_slave():
    """Setup slave server"""
    synnefo_ci = SynnefoCI(cleanup_config=True)
    # Get token from /nfs/token
    try:
        token = open("/nfs/synnefo_token").read().strip()
        synnefo_ci.write_config('token', token, 'Deployment')
    except:
        pass
    # Build slave server
    synnefo_ci.create_server()
    # Copy synnefo repo to server
    synnefo_ci.clone_repo()


if __name__ == "__main__":
    setup_slave()
