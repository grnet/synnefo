# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


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
