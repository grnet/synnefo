# Copyright (C) 2010-2016 GRNET S.A.
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

import string
from optparse import make_option
from synnefo.db import transaction

from synnefo.lib.ordereddict import OrderedDict
from synnefo.quotas import util
from synnefo.quotas import enforce
from synnefo.quotas import errors
from snf_django.management.commands import SynnefoCommand, CommandError
from snf_django.management.utils import pprint_table
from collections import defaultdict


SHUTDOWN_VM = "shutdown VM"
DELETE_VM = "delete VM"
DELETE_VOLUME = "delete volume"
DETACH_IP = "detach IP"
DELETE_IP = "delete IP"
RESOURCES_HELP = [
    ("cyclades.cpu", SHUTDOWN_VM, ""),
    ("cyclades.ram", SHUTDOWN_VM, ""),
    ("cyclades.vm", DELETE_VM, SHUTDOWN_VM),
    ("cyclades.disk", DELETE_VOLUME, ""),
    ("cyclades.total_cpu", DELETE_VM, SHUTDOWN_VM),
    ("cyclades.total_ram", DELETE_VM, SHUTDOWN_VM),
    ("cyclades.floating_ip", DELETE_IP, DETACH_IP),
]

DESTROY_RESOURCES = ["cyclades.vm",
                     "cyclades.total_cpu",
                     "cyclades.total_ram",
                     "cyclades.floating_ip",
                     ]


class Command(SynnefoCommand):
    help = """Check and fix quota violations for Cyclades resources.
    """

    command_option_list = (
        make_option("--max-operations",
                    help="Limit operations per backend."),
        make_option("--users", dest="users",
                    help=("Enforce resources only for the specified list "
                          "of users, e.g uuid1,uuid2")),
        make_option("--exclude-users",
                    help=("Exclude list of users from resource enforcement")),
        make_option("--projects",
                    help=("Enforce resources only for the specified list "
                          "of projects, e.g uuid1,uuid2")),
        make_option("--exclude-projects",
                    help=("Exclude list of projects from resource enforcement")
                    ),
        make_option("--resources",
                    help="Specify resources to check"),
        make_option("--soft-resources",
                    help="Specify resources to check for soft enforce"),
        make_option("--list-resources",
                    action="store_true",
                    default=False,
                    help="List available resources and respective actions"),
        make_option("--fix",
                    default=False,
                    action="store_true",
                    help="Fix violations"),
        make_option("--force",
                    default=False,
                    action="store_true",
                    help=("Confirm actions that may permanently "
                          "remove a VM, volume, or IP")),
        make_option("--shutdown-timeout",
                    help="Force vm shutdown after given seconds."),
        make_option("--remove-system-volumes",
                    default=False,
                    action="store_true",
                    help=("Allow removal of system volumes. This will also "
                          "remove the VM.")),
        make_option("--cascade-remove",
                    default=False,
                    action="store_true",
                    help=("Allow removal of a VM which has additional "
                          "(non system) volumes attached. This will also "
                          "remove these volumes")),
    )

    def help_resources(self, options):
        headers = ("Name", "Enforce action", "Soft enforce action")
        pprint_table(self.stdout, RESOURCES_HELP, headers,
                     options["output_format"], title="Resources")

    def confirm(self):
        self.stdout.write("Confirm? [y/N] ")
        try:
            response = raw_input()
        except EOFError:
            response = "ABORT"
        if string.lower(response) not in ['y', 'yes']:
            self.stderr.write("Aborted.\n")
            exit()

    def get_handlers(self, resources, resources_soft):
        def exists(v, from_soft=False):
            origin = resources_soft if from_soft else resources
            try:
                origin.remove(v)
                return True
            except KeyError:
                return False

        def check_unknown_left(resource_set, soft=False):
            if resource_set:
                m = ("'%s' is not a supported resource for %senforce"
                     % (resource_set.pop(), "soft " if soft else ""))
                raise CommandError(m)

        resources = set([] if resources is None
                        else resources.split(","))
        resources_soft = set([] if resources_soft is None
                             else resources_soft.split(","))
        if not resources.isdisjoint(resources_soft):
            raise CommandError("A resource shouldn't appear in both sets")

        handlers = []
        for handler in enforce.RESOURCE_HANDLING:
            resource_name = handler[0]
            is_soft = handler[1]
            if exists(resource_name, is_soft):
                handlers.append(handler)

        check_unknown_left(resources)
        check_unknown_left(resources_soft, soft=True)
        return handlers

    @transaction.commit_on_success
    def handle(self, *args, **options):
        write = self.stderr.write
        if options["list_resources"]:
            self.help_resources(options)
            exit()

        fix = options["fix"]
        force = options["force"]
        handlers = self.get_handlers(options["resources"],
                                     options["soft_resources"])
        maxops = options["max_operations"]
        if maxops is not None:
            try:
                maxops = int(maxops)
            except ValueError:
                m = "Expected integer max operations."
                raise CommandError(m)

        shutdown_timeout = options["shutdown_timeout"]
        if shutdown_timeout is not None:
            try:
                shutdown_timeout = int(shutdown_timeout)
            except ValueError:
                m = "Expected integer shutdown timeout."
                raise CommandError(m)

        remove_system_volumes = options["remove_system_volumes"]
        cascade_remove = options["cascade_remove"]

        excluded_users = options['exclude_users']
        excluded_users = set(excluded_users.split(',')
                             if excluded_users is not None else [])

        users_to_check = options['users']
        if users_to_check is not None:
            users_to_check = list(set(users_to_check.split(',')) -
                                  excluded_users)

        try:
            qh_holdings = util.get_qh_users_holdings(users_to_check)
        except errors.AstakosClientException as e:
            raise CommandError(e)

        excluded_projects = options["exclude_projects"]
        excluded_projects = set(excluded_projects.split(',')
                                if excluded_projects is not None else [])

        projects_to_check = options["projects"]
        if projects_to_check is not None:
            projects_to_check = list(set(projects_to_check.split(',')) -
                                     excluded_projects)

        try:
            qh_project_holdings = util.get_qh_project_holdings(
                projects_to_check)
        except errors.AstakosClientException as e:
            raise CommandError(e)

        qh_project_holdings = sorted(qh_project_holdings.items())
        qh_holdings = sorted(qh_holdings.items())
        resources = set(h[0] for h in handlers if not h[1])
        dangerous = bool(resources.intersection(DESTROY_RESOURCES))
        if resources:
            self.stderr.write("Checking resources %s...\n" %
                              ",".join(list(resources)))
        resources_soft = set(h[0] for h in handlers if h[1])
        if resources_soft:
            self.stderr.write("Checking resources for soft enforce %s...\n" %
                              ",".join(list(resources_soft)))
        if not resources and not resources_soft:
            self.stderr.write(
                "No resources specified; use '--list-resources' "
                "to list available resources.\n")
            exit()

        hopts = {"cascade_remove": cascade_remove,
                 "remove_system_volumes": remove_system_volumes,
                 }
        opts = {"shutdown_timeout": shutdown_timeout}
        actions = {}
        overlimit = []
        viol_id = 0
        remains = defaultdict(list)

        if users_to_check is None:
            for resource, is_soft, handle_resource, resource_type in handlers:
                if resource_type not in actions:
                    actions[resource_type] = OrderedDict()
                actual_resources = enforce.get_actual_resources(
                    resource_type, projects=projects_to_check)
                for project, project_quota in qh_project_holdings:
                    if enforce.skip_check(project, projects_to_check,
                                          excluded_projects):
                        continue
                    try:
                        qh = util.transform_project_quotas(project_quota)
                        qh_value, qh_limit, qh_pending = qh[resource]
                    except KeyError:
                        write("Resource '%s' does not exist in Quotaholder"
                              " for project '%s'!\n" %
                              (resource, project))
                        continue
                    if qh_pending:
                        write("Pending commission for project '%s', "
                              "resource '%s'. Skipping\n" %
                              (project, resource))
                        continue
                    diff = qh_value - qh_limit
                    if diff > 0:
                        viol_id += 1
                        overlimit.append((viol_id, "project", project, "",
                                          resource, qh_limit, qh_value))
                        relevant_resources = enforce.pick_project_resources(
                            actual_resources[project], users=users_to_check,
                            excluded_users=excluded_users)
                        handle_resource(viol_id, resource, relevant_resources,
                                        diff, actions, remains, options=hopts)

        for resource, is_soft, handle_resource, resource_type in handlers:
            if resource_type not in actions:
                actions[resource_type] = OrderedDict()
            actual_resources = enforce.get_actual_resources(resource_type,
                                                            users_to_check)
            for user, user_quota in qh_holdings:
                if enforce.skip_check(user, users_to_check, excluded_users):
                    continue
                for source, source_quota in user_quota.iteritems():
                    if enforce.skip_check(source, projects_to_check,
                                          excluded_projects):
                        continue
                    try:
                        qh = util.transform_quotas(source_quota)
                        qh_value, qh_limit, qh_pending = qh[resource]
                    except KeyError:
                        write("Resource '%s' does not exist in Quotaholder"
                              " for user '%s' and source '%s'!\n" %
                              (resource, user, source))
                        continue
                    if qh_pending:
                        write("Pending commission for user '%s', source '%s', "
                              "resource '%s'. Skipping\n" %
                              (user, source, resource))
                        continue
                    diff = qh_value - qh_limit
                    if diff > 0:
                        viol_id += 1
                        overlimit.append((viol_id, "user", user, source,
                                          resource, qh_limit, qh_value))
                        relevant_resources = actual_resources[source][user]
                        handle_resource(viol_id, resource, relevant_resources,
                                        diff, actions, remains, options=hopts)

        if not overlimit:
            write("No violations.\n")
            return

        headers = ("#", "Type", "Holder", "Source", "Resource", "Limit",
                   "Usage")
        pprint_table(self.stdout, overlimit, headers,
                     options["output_format"], title="Violations")

        if any(actions.values()):
            self.stdout.write("\n")
            if fix:
                if dangerous and not force:
                    write("You are enforcing resources that may permanently "
                          "remove a VM, volume, or IP.\n")
                    self.confirm()
                write("Applying actions. Please wait...\n")
            title = "Applied Actions" if fix else "Suggested Actions"
            log = enforce.perform_actions(actions, maxops=maxops, fix=fix,
                                          options=opts)
            headers = ("Type", "ID", "State", "Backend", "Action", "Violation")
            if fix:
                headers += ("Result",)
            pprint_table(self.stdout, log, headers,
                         options["output_format"], title=title)

        def explain(resource):
            if resource == "cyclades.disk":
                if not remove_system_volumes:
                    return (", because this would need to remove system "
                            "volumes; if you want to do so, use the "
                            "--remove-system-volumes option:")
                if not cascade_remove:
                    return (", because this would trigger the removal of "
                            "attached volumes, too; if you want to do "
                            "so, use the --cascade-remove option:")
            elif resource in DESTROY_RESOURCES:
                if not cascade_remove:
                    return (", because this would trigger the removal of "
                            "attached volumes, too; if you want to do "
                            "so, use the --cascade-remove option:")
            return ":"

        if remains:
            self.stderr.write("\n")
            for resource, viols in remains.iteritems():
                self.stderr.write(
                    "The following violations for resource '%s' "
                    "could not be resolved%s\n"
                    % (resource, explain(resource)))
                self.stderr.write("  %s\n" % ",".join(map(str, viols)))
