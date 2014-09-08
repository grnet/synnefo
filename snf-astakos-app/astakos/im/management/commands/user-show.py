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

from optparse import make_option
from astakos.im.models import AstakosUser, get_latest_terms, Project
from astakos.im.quotas import get_user_quotas

from synnefo.lib.ordereddict import OrderedDict
from snf_django.management.commands import SynnefoCommand, CommandError
from snf_django.management import utils

from ._common import show_user_quotas, style_options, check_style

import uuid


class Command(SynnefoCommand):
    args = "<user ID or email or uuid>"
    help = "Show user info"

    option_list = SynnefoCommand.option_list + (
        make_option('--quota',
                    action='store_true',
                    dest='list_quotas',
                    default=False,
                    help="Also list user quota"),
        make_option('--unit-style',
                    default='mb',
                    help=("Specify display unit for resource values "
                          "(one of %s); defaults to mb") % style_options),
        make_option('--projects',
                    action='store_true',
                    dest='list_projects',
                    default=False,
                    help="Also list project memberships"),
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a user ID or email")

        identifier = args[0]
        if identifier.isdigit():
            users = AstakosUser.objects.filter(id=int(identifier))
        else:
            try:
                uuid.UUID(identifier)
            except:
                users = AstakosUser.objects.filter(email__iexact=identifier)
            else:
                users = AstakosUser.objects.filter(uuid=identifier)
        if users.count() == 0:
            field = 'id' if identifier.isdigit() else 'email'
            msg = "Unknown user with %s '%s'" % (field, identifier)
            raise CommandError(msg)

        for user in users:
            kv = OrderedDict(
                [
                    ('id', user.id),
                    ('uuid', user.uuid),
                    ('status', user.status_display),
                    ('email', user.email),
                    ('first name', user.first_name),
                    ('last name', user.last_name),
                    ('admin', user.is_superuser),
                    ('last login', user.last_login),
                    ('date joined', user.date_joined),
                    ('last update', user.updated),
                    #('token', user.auth_token),
                    ('token expiration', user.auth_token_expires),
                    ('providers', user.auth_providers_display),
                    ('groups', [elem.name for elem in user.groups.all()]),
                    ('permissions', [elem.codename
                                     for elem in user.user_permissions.all()]),
                    ('group permissions', user.get_group_permissions()),
                    ('email_verified', user.email_verified),
                    ('moderated', user.moderated),
                    ('rejected', user.is_rejected),
                    ('active', user.is_active),
                    ('username', user.username),
                    ('activation_sent_date', user.activation_sent),
                    ('last_login_details', user.last_login_info_display),
                ])

            if get_latest_terms():
                has_signed_terms = user.signed_terms
                kv['has_signed_terms'] = has_signed_terms
                if has_signed_terms:
                    kv['date_signed_terms'] = user.date_signed_terms

            utils.pprint_table(self.stdout, [kv.values()], kv.keys(),
                               options["output_format"], vertical=True)

            if options["list_quotas"] and user.is_accepted():
                unit_style = options["unit_style"]
                check_style(unit_style)

                quotas = get_user_quotas(user)
                if quotas:
                    self.stdout.write("\n")
                    print_data, labels = show_user_quotas(quotas,
                                                          style=unit_style)
                    utils.pprint_table(self.stdout, print_data, labels,
                                       options["output_format"],
                                       title="User Quota")

            if options["list_projects"]:
                print_data, labels = ownerships(user)
                if print_data:
                    self.stdout.write("\n")
                    utils.pprint_table(self.stdout, print_data, labels,
                                       options["output_format"],
                                       title="Owned Projects")

                print_data, labels = memberships(user)
                if print_data:
                    self.stdout.write("\n")
                    utils.pprint_table(self.stdout, print_data, labels,
                                       options["output_format"],
                                       title="Project Memberships")


def memberships(user):
    ms = user.projectmembership_set.all()
    print_data = []
    labels = ('project id', 'project name', 'status')

    for m in ms:
        project = m.project
        print_data.append((project.uuid,
                           project.realname,
                           m.state_display(),
                           ))
    return print_data, labels


def ownerships(user):
    chains = Project.objects.select_related("last_application").\
        filter(owner=user)
    return chain_info(chains)


def chain_info(chains):
    labels = ('project id', 'project name', 'status', 'pending app id')
    l = []
    for project in chains:
        status = project.state_display()
        app = project.last_application
        pending_appid = app.id if app and app.state == app.PENDING else ""

        t = (project.uuid,
             project.realname,
             status,
             pending_appid,
             )
        l.append(t)
    return l, labels
