# Copyright 2014 GRNET S.A. All rights reserved.
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


def strcontext(user):
    if user is None:
        return ""
    return "user: %s, " % user


def get_qh_values(qh_values, user=None):
    prefix = "" if user is not None else "project_"
    try:
        usage = qh_values[prefix+"usage"]
        pending = qh_values[prefix+"pending"]
    except KeyError:
        raise AttributeError("Malformed quota response.")
    return usage, pending


def check_projects(stderr, resources, db_usage, qh_usage, user=None):
    write = stderr.write
    unsynced = []
    pending_exists = False
    unknown_exists = False

    projects = set(db_usage.keys())
    projects.update(qh_usage.keys())

    for project in projects:
        db_project_usage = db_usage.get(project, {})
        try:
            qh_project_usage = qh_usage[project]
        except KeyError:
            write("No holdings for %sproject: %s.\n"
                  % (strcontext(user), project))
            unknown_exists = True
            continue

        for resource in resources:
            db_value = db_project_usage.get(resource, 0)
            try:
                qh_values = qh_project_usage[resource]
            except KeyError:
                write("No holding for %sproject: %s, resource: %s.\n"
                      % (strcontext(user), project, resource))
                continue

            qh_value, qh_pending = get_qh_values(qh_values, user=user)
            if qh_pending:
                write("Pending commission for %sproject: %s, resource: %s.\n"
                      % (strcontext(user), project, resource))
                pending_exists = True
                continue
            if db_value != qh_value:
                tail = (resource, db_value, qh_value)
                head = (("project", project, None) if user is None
                        else ("user", user, project))
                unsynced.append(head + tail)
    return unsynced, pending_exists, unknown_exists


def check_users(stderr, resources, db_usage, qh_usage):
    write = stderr.write
    unsynced = []
    pending_exists = False
    unknown_exists = False

    users = set(db_usage.keys())
    users.update(qh_usage.keys())
    users.discard(None)

    for user in users:
        db_user_usage = db_usage.get(user, {})
        try:
            qh_user_usage = qh_usage[user]
        except KeyError:
            write("No holdings for user: %s.\n" % user)
            unknown_exists = True
            continue
        uns, pend, unkn = check_projects(stderr, resources,
                                         db_user_usage, qh_user_usage,
                                         user=user)
        unsynced += uns
        pending_exists = pending_exists or pend
        unknown_exists = unknown_exists or unkn
    return unsynced, pending_exists, unknown_exists


def create_user_provisions(provision_list):
    provisions = {}
    for _, holder, source, resource, db_value, qh_value in provision_list:
        provisions[(holder, source, resource)] = db_value - qh_value
    return provisions


def create_project_provisions(provision_list):
    provisions = {}
    for _, holder, _, resource, db_value, qh_value in provision_list:
        provisions[(holder, resource)] = db_value - qh_value
    return provisions
