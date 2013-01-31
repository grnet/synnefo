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
import random
import string

path = os.path.dirname(os.path.realpath(__file__))
os.environ['SYNNEFO_SETTINGS_DIR'] = path + '/settings'
os.environ['DJANGO_SETTINGS_MODULE'] = 'synnefo.settings'
from astakos.im.models import Chain, ProjectApplication, Project
from views import submit, approve

USAGE = "usage: submit-and-approve <user_id> <precursor id or name>"

def main():
    argv = sys.argv
    argc = len(sys.argv)

    if argc < 3:
        raise AttributeError(USAGE)
    try:
        user_id = int(argv[1])
        chain   = argv[2]
    except ValueError:
        raise AttributeError(USAGE)

    prec, name = resolve(chain)
    submit_and_approve(name, user_id, prec)

def rand_name():
    char_set = string.ascii_letters + string.digits
    return ''.join(random.sample(char_set, 6))

def resolve_chain(chain):
        state, project, app = chain.full_state()
        if state not in Chain.PENDING_STATES and project is not None:
            app = project.application
            return app.id, app.name
        else:
            return app.id, app.name

def resolve(chain):
    if chain is None:
        return None, rand_name()

    if chain.isdigit():
        try:
            chain = Chain.objects.get(chain=chain)
            return resolve_chain(chain)
        except:
            raise AttributeError('there is no chain %s' % (chain,))

    else:
        try:
            project = Project.objects.get(name=chain)
            return resolve_chain(project.id)
        except Project.DoesNotExist:
            try:
                apps = ProjectApplication.objects.filter(name=chain)
                last = apps.order_by('-id')[0]
                return last.id, chain
            except:
                return None, chain

def submit_and_approve(name, user_id, prec, times=20):
    for i in range(times):
        try:
            print '%s: submitting with precursor %s' % (i, prec)
            app_id = submit(name, user_id, prec)
            prec = app_id
        except Exception as e:
            raise e
        try:
            print '%s: approving application %s' % (i, app_id)
            approve(app_id)
        except Exception as e:
            raise e

if __name__ == "__main__":
    main()
