# Copyright (C) 2010-2017 GRNET S.A.
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

import sys
from optparse import make_option

from snf_django.lib.api import Credentials
from django.core.management.base import CommandError

from synnefo.management.common import (get_resource, convert_api_faults,
                                       wait_server_task)
from snf_django.management.commands import SynnefoCommand
from snf_django.management.utils import parse_bool
from synnefo.logic import servers, utils as logic_utils
from synnefo.api.util import (make_tag, COMPUTE_API_TAG_USER_PREFIX,
                              COMPUTE_API_TAG_SYSTEM_PREFIX)


ACTIONS = ["start", "stop", "reboot_hard", "reboot_soft", "rescue", "unrescue"]


class Command(SynnefoCommand):
    args = "<server_id>"
    help = "Modify a server."

    option_list = SynnefoCommand.option_list + (
        make_option(
            '--name',
            dest='name',
            metavar='NAME',
            help="Rename server."),
        make_option(
            '--user',
            dest='user',
            metavar='USER_UUID',
            help="Change ownership of server. Value must be a user UUID."
                 " This also changes the ownership of all volumes, NICs, and"
                 " IPs attached to the server. Finally, it assigns the"
                 " volumes, IPs, and the server to the system project of the"
                 " destination user."),
        make_option(
            "--suspended",
            dest="suspended",
            default=None,
            choices=["True", "False"],
            metavar="True|False",
            help="Mark a server as suspended/non-suspended."),
        make_option(
            "--flavor",
            dest="flavor",
            metavar="FLAVOR_ID",
            help="Resize a server by modifying its flavor. The new flavor"
                 " must have the same disk size and disk template."),
        make_option(
            "--action",
            dest="action",
            choices=ACTIONS,
            metavar="|".join(ACTIONS),
            help="Perform one of the allowed actions."),
        make_option(
            "--wait",
            dest="wait",
            default="True",
            choices=["True", "False"],
            metavar="True|False",
            help="Wait for Ganeti jobs to complete. [Default: True]"),
        make_option(
            '--tag-add',
            dest='tag_add',
            metavar='ADD_TAG',
            help="Add tag to server."),
        make_option(
            '--tag-delete',
            dest='tag_delete',
            metavar='DELETE_TAG',
            help="Delete tag from server."),
        make_option(
            '--tag-delete-all',
            action='store_true',
            dest='tag_delete_all',
            default=False,
            help="Delete all tags from server."),
        make_option(
            '--tag-replace-all',
            dest='tag_replace_all',
            metavar='REPLACE_TAGS',
            help="Replace all of a server's tags with a new comma-separated "
                 "list of tags."),
        make_option(
            '--tag-namespace',
            dest='tag_namespace',
            default='user',
            choices=['user', 'system'],
            metavar='user|system',
            help="Set server tag namespace (default=user)."),
    )

    @convert_api_faults
    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a server ID")

        server_id = args[0]
        server = get_resource("server", server_id)

        credentials = Credentials("snf-manage", is_admin=True)
        new_name = options.get("name", None)
        if new_name is not None:
            old_name = server.name
            server = servers.rename(server_id, new_name, credentials)
            self.stdout.write("Renamed server '%s' from '%s' to '%s'\n" %
                              (server, old_name, new_name))

        suspended = options.get("suspended", None)
        if suspended is not None:
            suspended = parse_bool(suspended)
            server = servers.suspend(server_id, suspended, credentials)
            self.stdout.write("Set server '%s' as suspended=%s\n" %
                              (server, suspended))

        new_owner = options.get('user')
        if new_owner is not None:
            if "@" in new_owner:
                raise CommandError("Invalid user UUID.")
            if new_owner == server.userid:
                self.stdout.write("%s is already server owner.\n" % new_owner)
            else:
                servers.change_owner(server_id, new_owner, credentials)
                self.stdout.write(
                    "WARNING: User quotas should be out of sync now,"
                    " run `snf-manage reconcile-resources-cyclades'"
                    " to review and update them.\n")

        wait = parse_bool(options["wait"])
        new_flavor_id = options.get("flavor")
        if new_flavor_id is not None:
            new_flavor = get_resource("flavor", new_flavor_id)
            old_flavor = server.flavor
            msg = "Resizing server '%s' from flavor '%s' to '%s'.\n"
            self.stdout.write(msg % (server, old_flavor, new_flavor))
            server = servers.resize(server_id, new_flavor, credentials)
            wait_server_task(server, wait, stdout=self.stdout)

        action = options.get("action")
        if action is not None:
            if action == "start":
                server = servers.start(server_id, credentials=credentials)
            elif action == "stop":
                server = servers.stop(server_id, credentials=credentials)
            elif action == "reboot_hard":
                server = servers.reboot(server_id, reboot_type="HARD",
                                        credentials=credentials)
            elif action == "reboot_soft":
                server = servers.reboot(server_id, reboot_type="SOFT",
                                        credentials=credentials)
            elif action == "rescue":
                server = servers.rescue(server_id, credentials=credentials)
            elif action == "unrescue":
                server = servers.unrescue(server_id, credentials=credentials)
            else:
                raise CommandError("Unknown action.")
            wait_server_task(server, wait, stdout=self.stdout)

        tag_namespace = options.get('tag_namespace')
        if tag_namespace is None or tag_namespace == 'user':
            prefix = COMPUTE_API_TAG_USER_PREFIX
            tag_namespace = 'user'
        else:
            prefix = COMPUTE_API_TAG_SYSTEM_PREFIX

        tag_add = options.get('tag_add')
        if tag_add is not None:
            tag = make_tag(tag_add, tag_namespace)
            servers.add_tag(server_id, credentials, tag)
            self.stdout.write("Added tag '%s' in namespace '%s' to server "
                              "'%s'\n" % (tag_add, tag_namespace,
                                          server.name))
            wait_server_task(server, wait, stdout=self.stdout)

        tag_delete = options.get('tag_delete')
        if tag_delete is not None:
            tag = make_tag(tag_delete, tag_namespace)
            servers.delete_tag(server_id, credentials, tag)
            self.stdout.write("Deleted tag '%s' in namespace '%s' from server "
                              "'%s'\n" % (tag_delete, tag_namespace,
                                          server.name))
            wait_server_task(server, wait, stdout=self.stdout)

        tag_delete_all = options.get('tag_delete_all')
        if tag_delete_all:
            servers.delete_tags(server_id, credentials, prefix)
            self.stdout.write("Deleted server's '%s' tags in namespace '%s'\n"
                              % (server.name, tag_namespace))
            wait_server_task(server, wait, stdout=self.stdout)

        tag_replace_all = options.get('tag_replace_all')
        if tag_replace_all:
            tag_replace_all = tag_replace_all.split(',')
            tags = [make_tag(tag, tag_namespace)
                    for tag in tag_replace_all]
            servers.replace_tags(server_id, credentials, prefix, tags)
            self.stdout.write("Replaced server's '%s' tags in namespace '%s'"
                              " with the following set: '%s'\n" %
                              (server.name, tag_namespace,
                               [tag.encode('utf-8') for tag in
                                tag_replace_all]))
            wait_server_task(server, wait, stdout=self.stdout)
