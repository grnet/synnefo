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

import os
import re
import sys
import datetime
import logging
from optparse import (make_option, OptionParser, OptionGroup,
                      TitledHelpFormatter)
from synnefo import settings
from django.core.management.base import (BaseCommand,
                                         CommandError as DjangoCommandError)
from django.core.exceptions import FieldError
from snf_django.management import utils
from snf_django.lib.astakos import UserCache
from snf_django.utils.line_logging import NewlineStreamHandler

import distutils

USER_EMAIL_FIELD = "user.email"
LOGGER_EXCLUDE_COMMANDS = "-list$|-show$"


class SynnefoOutputWrapper(object):
    """Wrapper around stdout/stderr

    This class replaces Django's 'OutputWrapper' which doesn't handle
    logging to file.

    Since 'BaseCommand' doesn't initialize the 'stdout' and 'stderr'
    attributes at '__init__' but sets them only when it needs to,
    this class has to be a descriptor.

    We will use the old 'OutputWrapper' class for print to the screen and
    a logger for logging to the file.

    """
    def __init__(self):
        self.django_wrapper = None
        self.logger = None

    def __set__(self, obj, value):
        self.django_wrapper = value

    def __getattr__(self, name):
        return getattr(self.django_wrapper, name)

    def write(self, msg, *args, **kwargs):
        if self.logger is not None:
            self.logger.info(msg)
        if self.django_wrapper is not None:
            self.django_wrapper.write(msg, *args, **kwargs)


class CommandError(DjangoCommandError):
    def __str__(self):
        return utils.smart_locale_str(self.message, errors='replace')


class SynnefoCommandFormatter(TitledHelpFormatter):
    def format_heading(self, heading):
        if heading == "Options":
            return ""
        return "%s\n%s\n" % (heading, "=-"[self.level] * len(heading))


class SynnefoCommand(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option(
            "--output-format",
            dest="output_format",
            metavar="[pretty, csv, json]",
            default="pretty",
            choices=["pretty", "csv", "json"],
            help="Select the output format: pretty [the default], json, "
                 "csv [comma-separated output]"),
    )

    stdout = SynnefoOutputWrapper()
    stderr = SynnefoOutputWrapper()

    def run_from_argv(self, argv):
        """Initialize loggers and convert arguments to unicode objects

        Create a filename based on the timestamp, the running
        command and the pid. Then create a new logger that will
        write to this file and pass it to stdout and stderr
        'SynnefoOutputWrapper' objects.

        Modify all existing loggers to write to this file as well.

        Commands that match the 'LOGGER_EXCLUE_COMMANDS' pattern will not be
        logged (by default all *-list and *-show commands).

        Also, convert command line arguments and options to unicode objects
        using user's preferred encoding.

        """
        curr_time = datetime.datetime.now()
        curr_time = datetime.datetime.strftime(curr_time, "%y%m%d%H%M%S")
        command = argv[1]
        pid = os.getpid()
        fd = None
        stream = None

        exclude_commands = getattr(settings, "LOGGER_EXCLUDE_COMMANDS",
                                   LOGGER_EXCLUDE_COMMANDS)
        if re.search(exclude_commands, command) is None:
            # The filename will be of the form time_command_pid.log
            basename = "%s_%s_%s" % (curr_time, command, pid)
            log_dir = os.path.join(settings.LOG_DIR, "commands")
            # If log_dir is missing, create it
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            filename = os.path.join(log_dir, basename + ".log")

            try:
                fd = os.open(filename,
                             os.O_RDWR | os.O_APPEND | os.O_CREAT,
                             0600)
                stream = os.fdopen(fd, 'a')

                formatter = logging.Formatter(
                    "%(asctime)s - %(levelname)s: %(message)s")
                # Our file handler
                # We need one handler without newline terminator
                # for commnand-line's output (the programmer is
                # responsible for formatting the output) and one
                # FileHandler for the rest loggers.
                # TODO: Replace 'NewlineStreamHandler' with pythons
                # 'logging.StreamHandler' when python version >= 3.2
                line_handler = NewlineStreamHandler(stream)
                line_handler.terminator = ''
                line_handler.setLevel(logging.DEBUG)
                line_handler.setFormatter(formatter)

                file_handler = logging.FileHandler(filename, mode='a')
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)

                # Change all loggers to use our new file_handler
                all_loggers = logging.Logger.manager.loggerDict.keys()
                for logger_name in all_loggers:
                    logger = logging.getLogger(logger_name)
                    logger.addHandler(file_handler)

                # Create our new logger
                logger = logging.getLogger(basename)
                logger.setLevel(logging.DEBUG)
                logger.propagate = False
                logger.addHandler(line_handler)

                # Write the command which is executed
                header = "\n\tcommand: %s\n\tpid: %s\n" \
                    % (" ".join(map(str, argv)), pid)
                logger.info(header + "\n\nOutput:\n")

                # Give the logger to our stdout, stderr objects
                self.stdout.logger = logger
                self.stderr.logger = logger
            except OSError as err:
                msg = ("Could not open file %s for write: %s\n"
                       "Will not log this command's output\n") % (
                    filename, err)
                sys.stderr.write(msg)

        argv = [utils.smart_locale_unicode(a) for a in argv]
        super(SynnefoCommand, self).run_from_argv(argv)

        if stream is not None:
            stream.close()
            fd = None
        if fd is not None:
            os.close(fd)

    def create_parser(self, prog_name, subcommand):
        parser = OptionParser(prog=prog_name, add_help_option=False,
                              formatter=SynnefoCommandFormatter())

        parser.set_usage(self.usage(subcommand))
        parser.version = self.get_version()

        # Handle Django's and common options
        common_options = OptionGroup(parser, "Common Options")
        common_options.add_option("-h", "--help", action="help",
                                  help="show this help message and exit")

        common_options.add_option("--version", action="version",
                                  help="show program's version number and"
                                       "  exit")
        [common_options.add_option(o) for o in self.option_list]
        if common_options.option_list:
            parser.add_option_group(common_options)

        # Handle command specific options
        command_options = OptionGroup(parser, "Command Specific Options")
        [command_options.add_option(o)
         for o in getattr(self, "command_option_list", ())]
        if command_options.option_list:
            parser.add_option_group(command_options)

        return parser

    def pprint_table(self, *args, **kwargs):
        utils.pprint_table(self.stdout, *args, **kwargs)


class ListCommand(SynnefoCommand):
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
    astakos_auth_url = None
    astakos_token = None

    # Optimize DB queries
    prefetch_related = []
    select_related = []

    help = "Generic List Command"
    option_list = SynnefoCommand.option_list + (
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
    )

    def __init__(self, *args, **kwargs):
        if self.user_uuid_field:
            assert(self.astakos_auth_url), "astakos_auth_url attribute is "\
                                           "needed when user_uuid_field "\
                                           "is declared"
            assert(self.astakos_token), "astakos_token attribute is needed"\
                                        " when user_uuid_field is declared"
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

        # If an user field is declared, include the USER_EMAIL_FIELD in the
        # available fields
        if self.user_uuid_field is not None:
            self.FIELDS[USER_EMAIL_FIELD] =\
                ("_user_email", "The email of the owner")

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

        # --display-mails option
        if options.get("display_mails"):
            self.fields.append(USER_EMAIL_FIELD)

        # --filter-by option
        if options["filter_by"]:
            filters, excludes = \
                utils.parse_queryset_filters(options["filter_by"])
        else:
            filters, excludes = ({}, {})

        self.filters.update(filters)
        self.excludes.update(excludes)

        # --user option
        user = options.get("user")
        if user:
            if "@" in user:
                ucache = UserCache(self.astakos_auth_url, self.astakos_token)
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

        select_related = getattr(self, "select_related", [])
        prefetch_related = getattr(self, "prefetch_related", [])

        objects = self.object_class.objects
        try:
            if select_related:
                objects = objects.select_related(*select_related)
            if prefetch_related:
                objects = objects.prefetch_related(*prefetch_related)
            objects = objects.filter(**self.filters)
            for key, value in self.excludes.iteritems():
                objects = objects.exclude(**{key: value})
        except FieldError as e:
            raise CommandError(e)
        except Exception as e:
            raise CommandError("Can not filter results: %s" % e)

        order_key = self.order_by if self.order_by is not None else 'pk'
        objects = objects.order_by(order_key)

        if USER_EMAIL_FIELD in self.fields:
            if '_user_email' in self.object_class._meta.get_all_field_names():
                raise RuntimeError("%s has already a 'user_mail' attribute")
            uuids = [getattr(obj, self.user_uuid_field) for obj in objects]
            ucache = UserCache(self.astakos_auth_url, self.astakos_token)
            ucache.fetch_names(list(set(uuids)))
            for obj in objects:
                uuid = getattr(obj, self.user_uuid_field)
                obj._user_email = ucache.get_name(uuid)

        # Special handling of DB results
        objects = list(objects)
        self.handle_db_objects(objects, **options)

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

    def handle_db_objects(self, objects, **options):
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
        headers = ["Filter", "Description"]
        table = []
        for field in self.object_class._meta.fields:
            table.append((field.name, field.verbose_name))
        utils.pprint_table(self.stdout, table, headers)


class RemoveCommand(SynnefoCommand):
    help = "Generic remove command"

    command_option_list = (
        make_option(
            "-f", "--force",
            dest="force",
            action="store_true",
            default=False,
            help="Do not prompt for confirmation"),
    )

    def confirm_deletion(self, force, resource='', args=''):
        if force is True:
            return True

        ids = ', '.join(args)
        self.stdout.write("Are you sure you want to delete %s %s?"
                          " [Y/N] " % (resource, ids))
        try:
            answer = distutils.util.strtobool(raw_input())
            if answer != 1:
                raise CommandError("Aborting deletion")
        except ValueError:
            raise CommandError("Unaccepted input value. Please choose yes/no"
                               " (y/n).")
