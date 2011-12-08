#!/usr/bin/env python

# Copyright 2011 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

"""
A tool that connects to the Pithos backend and returns the size and contents
of a pithos object.

Since the backend does not have a "root" account we use the account given in
the URL as the user when connecting to the backend.
"""

try:
    from synnefo import settings
except ImportError:
    raise Exception("Cannot import settings, make sure PYTHONPATH contains "
                    "the parent directory of the Synnefo Django project.")

from django.core.management import setup_environ
setup_environ(settings)

from optparse import OptionParser
from sys import exit, stdout

from django.conf import settings
from pithos.backends import connect_backend


backend = connect_backend()
parser = OptionParser()
parser.add_option('-s', action='store_true', dest='size', default=False,
        help='print file size and exit')


def urlsplit(url):
    """Returns (accout, container, object) from a location string"""
    
    assert url.startswith('pithos://'), "Invalid URL"
    t = url.split('/', 4)
    assert len(t) == 5, "Invalid URL"
    return t[2:5]


def print_size(url):
    """Writes object's size to stdout."""
    
    account, container, object = urlsplit(url)
    meta = backend.get_object_meta(account, account, container, object)
    print meta['bytes']


def print_data(url):
    """Writes object's size to stdout."""
    
    account, container, object = urlsplit(url)
    size, hashmap = backend.get_object_hashmap(account, account, container,
            object)
    for hash in hashmap:
        block = backend.get_block(hash)
        stdout.write(block)
    

def main():
    options, args = parser.parse_args()
    if len(args) != 1:
        parser.print_help()
        exit(1)
    
    url = args[0]
    if options.size:
        print_size(url)
    else:
        print_data(url)

if __name__ == '__main__':
    main()
