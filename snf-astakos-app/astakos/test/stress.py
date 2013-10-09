#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
from optparse import OptionParser
from time import sleep
import threading
import datetime
from random import choice, randint
import logging

path = os.path.dirname(os.path.realpath(__file__))
os.environ['SYNNEFO_SETTINGS_DIR'] = path + '/settings'
os.environ['DJANGO_SETTINGS_MODULE'] = 'synnefo.settings'

from django.db import transaction
from astakos.im.models import AstakosUser
from astakos.im.functions import ProjectError
from astakos.im import quotas
from views import submit, approve, join, leave

USERS = {}
PROJECTS = {}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def random_name():
    alphabet = u'abcdef_123490αβγδεζ'
    length = randint(1, 15)
    return ''.join(choice(alphabet) for _ in xrange(length))


def random_email():
    alphabet = u'abcdef_123490'
    length = randint(1, 10)
    first = ''.join(choice(alphabet) for _ in xrange(length))

    alphabet = u'abcdef'
    length = randint(2, 4)
    last = ''.join(choice(alphabet) for _ in xrange(length))
    return first + '@' + last + '.com'


def new_user():
    email = random_email()
    defaults = {'first_name': random_name(),
                'last_name': random_name(),
                'is_active': True,
                }
    u, created = AstakosUser.objects.get_or_create(
        email=email, defaults=defaults)
    if created:
        quotas.qh_sync_user(u)
        return u
    return None


@transaction.commit_on_success
def new_users(count):
    for i in range(count):
        while True:
            u = new_user()
            if u is not None:
                USERS[u.id] = u
                break


class SubmitApproveT(threading.Thread):
    def __init__(self, *args, **kwargs):
        self.repeat = kwargs.pop('repeat', 1)
        threading.Thread.__init__(self, *args, **kwargs)

    def run(self):
        owner = choice(USERS.keys())
        p_name = random_name()
        submit_and_approve(p_name, owner, None, self.repeat,
                           prefix=self.name)


def submit_and_approve(name, user_id, project_id, repeat, prefix=""):
    if prefix:
        prefix += ' '

    for i in range(repeat):
        try:
            now = datetime.datetime.now()
            logger.info('%s%s: submitting for project %s'
                        % (prefix, now, project_id))
            app_id, project_id = submit(name, user_id, project_id)
        except ProjectError as e:
            logger.info(e.message)
            continue
        except Exception as e:
            logger.exception(e)
            continue
        try:
            now = datetime.datetime.now()
            logger.info('%s%s: approving application %s of project %s'
                        % (prefix, now, app_id, project_id))
            approve(app_id)
            PROJECTS[project_id] = True
        except Exception as e:
            logger.exception(e)


class JoinLeaveT(threading.Thread):
    def __init__(self, *args, **kwargs):
        self.repeat = kwargs.pop('repeat', 1)
        threading.Thread.__init__(self, *args, **kwargs)

    def run(self):
        user = choice(USERS.values())
        while True:
            projects = PROJECTS.keys()
            if projects:
                pid = choice(projects)
                break
            sleep(0.1)
        join_and_leave(pid, user, self.repeat, prefix=self.name)


def join_and_leave(proj_id, user, repeat, prefix=""):
    user_id = user.id
    if prefix:
        prefix += ' '

    for i in range(repeat):
        try:
            now = datetime.datetime.now()
            logger.info('%s%s: user %s joining project %s'
                        % (prefix, now, user_id, proj_id))
            membership = join(proj_id, user)
        except ProjectError as e:
            logger.info(e.message)
            continue
        except Exception as e:
            logger.exception(e)
            continue
        try:
            now = datetime.datetime.now()
            logger.info('%s%s: user %s leaving project %s'
                        % (prefix, now, user_id, proj_id))
            leave(membership.id, user)
        except ProjectError as e:
            logger.info(e.message)
        except Exception as e:
            logger.exception(e)


def test(users, projects, memb, repeat):
    logging.basicConfig()

    new_users(users)

    for i in range(projects):
        SubmitApproveT(repeat=repeat).start()

    for i in range(memb):
        JoinLeaveT(repeat=repeat).start()

    for thread in threading.enumerate():
        if thread is not threading.currentThread():
            thread.join()


def main():
    parser = OptionParser()
    parser.add_option('--users',
                      dest='users',
                      default=2,
                      help="Number of users (default=2)")
    parser.add_option('--projects',
                      dest='projects',
                      default=2,
                      help="Number of projects (default=2)")
    parser.add_option('--memb',
                      dest='memb',
                      default=2,
                      help="Number of membership requests (default=2)")
    parser.add_option('--repeat',
                      dest='repeat',
                      default=20,
                      help="Number of iterations (default=20)")
    parser.add_option('-q', '--quiet',
                      action='store_true',
                      dest='quiet',
                      default=False,
                      help="Print only errors")

    (options, args) = parser.parse_args()

    if options.quiet:
        logger.setLevel(logging.WARNING)

    users = int(options.users)
    projects = int(options.projects)
    memb = int(options.memb)
    repeat = int(options.repeat)
    test(users, projects, memb, repeat)


if __name__ == "__main__":
    main()
