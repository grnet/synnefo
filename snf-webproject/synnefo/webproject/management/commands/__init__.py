# Copyright 2012-2013 GRNET S.A. All rights reserved.
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

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import FieldError

from synnefo.webproject.management import utils
from snf_django.lib.astakos import UserCache


class SynnefoCommand(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option(
            "--output-format",
            dest="output_format",
            metavar="[pretty, csv, json]",
            default="pretty",
            choices=["pretty", "csv", "json"],
            help="Select the output format: pretty [the default], tabs"
                 " [tab-separated output], csv [comma-separated output]"),
    )


class ListCommand(BaseCommand):
    """Generic *-list management command.

    Management command to handle common tasks when implementing a -list
    management command. This class handles the following tasks:

    * Retrieving objects from database.

    The DB model class is declared in ``object_class`` class attribute. Also,
    results can be filter using either the ``filters`` and ``excludes``
    attribute or the "--filter-by" option.

    * Display specific fields of the database objects.

    List of available fields is defined in the ``FIELDS`` class attribute,
    which is a dictionary mapping from field names to tuples containing the
    way the field is retrieved and a text help message to display. The first
    field of the tuple is either a string containing a chain of attribute
    accesses (e.g. "machine.flavor.cpu") either a callable function, taking
    as argument the DB object and returning a single value.

    The fields that will be displayed be default is contained in the ``fields``
    class attribute. The user can specify different fields using the "--fields"
    option.

    * Handling of user UUIDs and names.

    If the ``user_uuid_field`` is declared, then "--user" and "--display-mails"
    options will become available. The first one allows filtering via either
    a user's UUID or display name. The "--displayname" option will append
    the displayname of ther user with "user_uuid_field" to the output.

    * Pretty printing output to a nice table.

    """

    # The following fields must be handled in the ListCommand subclasses!

    # The django DB model
    object_class = None
    # The name of the field containg the user ID of the user, if any.
    user_uuid_field = None
    # The name of the field containg the deleted flag, if any.
    deleted_field = None
    # Dictionary with all available fields
    FIELDS = {}
    # List of fields to display by default
    fields = []
    # Default filters and excludes
    filters = {}
    excludes = {}
    # Order results
    order_by = None

    # Fields used only with user_user_field
    astakos_url = None
    astakos_token = None

    help = "Generic List Command"
    option_list = BaseCommand.option_list + (
        make_option(
            "-o", "--output",
            dest="fields",
            help="Comma-separated list of output fields"),
        make_option(
            "--list-fields",
            dest="list_fields",
            action="store_true",
            default=False,
            help="List available output fields"),
        make_option(
            "--filter-by",
            dest="filter_by",
            metavar="FILTERS",
            help="Filter results. Comma separated list of key `cond` val pairs"
                 " that displayed entries must satisfy. e.g."
                 " --filter-by \"deleted=False,id>=22\"."),
        make_option(
            "--list-filters",
            dest="list_filters",
            action="store_true",
            default=False,
            help="List available filters"),
        make_option(
            "--no-headers",
            dest="headers",
            action="store_false",
            default=True,
            help="Do not display headers"),
        make_option(
            "--output-format",
            dest="output_format",
            metavar="[pretty, csv, json]",
            default="pretty",
            choices=["pretty", "csv", "json"],
            help="Select the output format: pretty [the default], tabs"
                 " [tab-separated output], csv [comma-separated output]"),
    )

    def __init__(self, *args, **kwargs):
        if self.user_uuid_field:
            assert(self.astakos_url), "astakos_url attribute is needed when"\
                                      " user_uuid_field is declared"
            assert(self.astakos_token), "astakos_token attribute is needed"\
                                        " user_uuid_field is declared"
            self.option_list += (
                make_option(
                    "-u", "--user",
                    dest="user",
                    metavar="USER",
                    help="List items only for this user."
                         " 'USER' can be either a user UUID or a display"
                         " name"),
                make_option(
                    "--display-mails",
                    dest="display_mails",
                    action="store_true",
                    default=False,
                    help="Include the user's email"),
            )

        if self.deleted_field:
            self.option_list += (
                make_option(
                    "-d", "--deleted",
                    dest="deleted",
                    action="store_true",
                    help="Display only deleted items"),
            )
        super(ListCommand, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        if len(args) > 0:
            raise CommandError("List commands do not accept any argument")

        assert(self.object_class), "object_class variable must be declared"

        if options["list_fields"]:
            self.display_fields()
            return

        if options["list_filters"]:
            self.display_filters()
            return

        # --output option
        if options["fields"]:
            fields = options["fields"]
            fields = fields.split(",")
            self.validate_fields(fields)
            self.fields = options["fields"].split(",")

        # --filter-by option
        if options["filter_by"]:
            filters, excludes = utils.parse_filters(options["filter_by"])
        else:
            filters, excludes = ({}, {})

        self.filters.update(filters)
        self.excludes.update(excludes)

        # --user option
        user = options.get("user")
        if user:
            if "@" in user:
                ucache = UserCache(self.astakos_url, self.astakos_token)
                user = ucache.get_uuid(user)
            self.filters[self.user_uuid_field] = user

        # --deleted option
        if self.deleted_field:
            deleted = options.get("deleted")
            if deleted:
                self.filters[self.deleted_field] = True
            else:
                self.filters[self.deleted_field] = False

        # Special handling of arguments
        self.handle_args(self, *args, **options)

        objects = self.object_class.objects
        try:
            objects = objects.filter(**self.filters)
            objects = objects.exclude(**self.excludes)
        except FieldError as e:
            raise CommandError(e)
        except Exception as e:
            raise CommandError("Can not filter results: %s" % e)

        order_key = self.order_by if self.order_by is not None else 'pk'
        objects = objects.order_by(order_key)

        # --display-mails option
        display_mails = options.get("display_mails")
        if display_mails:
            if 'user_mail' in self.object_class._meta.get_all_field_names():
                raise RuntimeError("%s has already a 'user_mail' attribute")

            self.fields.append("user.email")
            self.FIELDS["user.email"] =\
                ("user_email", "The email of the owner.")
            uuids = [getattr(obj, self.user_uuid_field) for obj in objects]
            ucache = UserCache(self.astakos_url, self.astakos_token)
            ucache.fetch_names(list(set(uuids)))
            for obj in objects:
                uuid = getattr(obj, self.user_uuid_field)
                obj.user_email = ucache.get_name(uuid)

        # Special handling of DB results
        self.handle_db_objects(objects)

        headers = self.fields
        columns = [self.FIELDS[key][0] for key in headers]

        table = []
        for obj in objects:
            row = []
            for attr in columns:
                if callable(attr):
                    row.append(attr(obj))
                else:
                    item = obj
                    attrs = attr.split(".")
                    for attr in attrs:
                        item = getattr(item, attr)
                    row.append(item)
            table.append(row)

        # Special handle of output
        self.handle_output(table, headers)

        # Print output
        output_format = options["output_format"]
        if output_format != "json" and not options["headers"]:
            headers = None
        utils.pprint_table(self.stdout, table, headers, output_format)

    def handle_args(self, *args, **kwargs):
        pass

    def handle_db_objects(self, objects):
        pass

    def handle_output(self, table, headers):
        pass

    def display_fields(self):
        headers = ["Field", "Description"]
        table = []
        for field, (_, help_msg) in self.FIELDS.items():
            table.append((field, help_msg))
        utils.pprint_table(self.stdout, table, headers)

    def validate_fields(self, fields):
        for f in fields:
            if f not in self.FIELDS.keys():
                raise CommandError("Unknown field '%s'. 'Use --list-fields"
                                   " option to find out available fields."
                                   % f)

    def display_filters(self):
        headers = ["Filter", "Description", "Help"]
        table = []
        for field in self.object_class._meta.fields:
            table.append((field.name, field.verbose_name, field.help_text))
        utils.pprint_table(self.stdout, table, headers)
