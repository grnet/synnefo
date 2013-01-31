#!/usr/bin/env python

# Copyright 2013 GRNET S.A. All rights reserved.
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

import os
import sys

path = os.path.dirname(os.path.realpath(__file__))
os.environ['SYNNEFO_SETTINGS_DIR'] = path + '/settings'
os.environ['DJANGO_SETTINGS_MODULE'] = 'synnefo.settings'

from astakos.im.functions import get_project_by_name, get_project_by_id
from views import join, leave

USAGE = "usage: join-and-leave <user_id> <project_id or name>"

def main():
    argv = sys.argv
    argc = len(sys.argv)

    if argc < 3:
        raise AttributeError(USAGE)
    try:
        user_id = int(argv[1])
        proj = argv[2]
    except ValueError:
        raise AttributeError(USAGE)

    proj_id = resolve(proj)
    join_and_leave(proj_id, user_id)

def resolve(proj):
    if proj.isdigit():
        return proj
    else:
        try:
            return get_project_by_name(proj).id
        except:
            AttributeError(USAGE)

def join_and_leave(proj_id, user_id, times=20):
    for i in range(times):
        try:
            print '%s: joining project %s' % (i, proj_id)
            join(proj_id, user_id)
        except Exception as e:
            print e
        try:
            print '%s: leaving project %s' % (i, proj_id)
            leave(proj_id, user_id)
        except Exception as e:
            print e


if __name__ == "__main__":
    main()
