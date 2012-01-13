#!/usr/bin/env python

from django.core.management import ManagementUtility, setup_environ, \
BaseCommand, LaxOptionParser, handle_default_options

from optparse import Option, make_option
from synnefo.util.version import get_component_version

import sys
import os

class SynnefoManagementUtility(ManagementUtility):
    """
    Override django ManagementUtility to allow us provide a custom
    --settings-dir option for synnefo application.

    Most of the following code is a copy from django.core.management module
    """

    def execute(self):
        """
        Given the command-line arguments, this figures out which subcommand is
        being run, creates a parser appropriate to that command, and runs it.
        """

        # --settings-dir option
        # will remove it later to avoid django commands from raising errors
        option_list = BaseCommand.option_list + (
            make_option('--settings-dir',
                action='store',
                dest='settings_dir',
                default=None,
                help='Load *.conf files from directory as settings'),)

        # Preprocess options to extract --settings and --pythonpath.
        # These options could affect the commands that are available, so they
        # must be processed early.
        parser = LaxOptionParser(usage="%prog subcommand [options] [args]",
                                 version=get_component_version('webproject'),
                                 option_list=option_list)
        self.autocomplete()
        try:
            options, args = parser.parse_args(self.argv)
            handle_default_options(options)
        except:
            pass # Ignore any option errors at this point.

        # user provides custom settings dir
        # set it as environmental variable and remove it from self.argv
        if options.settings_dir:
            os.environ['SYNNEFO_SETTINGS_DIR'] = options.settings_dir
            for arg in self.argv:
                if arg.startswith('--settings-dir'):
                    self.argv.remove(arg)

        try:
            subcommand = self.argv[1]
        except IndexError:
            subcommand = 'help' # Display help if no arguments were given.

        if subcommand == 'help':
            if len(args) > 2:
                self.fetch_command(args[2]).print_help(self.prog_name, args[2])
            else:
                parser.print_lax_help()
                sys.stdout.write(self.main_help_text() + '\n')
                sys.exit(1)
        # Special-cases: We want 'django-admin.py --version' and
        # 'django-admin.py --help' to work, for backwards compatibility.
        elif self.argv[1:] == ['--version']:
            # LaxOptionParser already takes care of printing the version.
            pass
        elif self.argv[1:] in (['--help'], ['-h']):
            parser.print_lax_help()
            sys.stdout.write(self.main_help_text() + '\n')
        else:
            self.fetch_command(subcommand).run_from_argv(self.argv)

def main():
    # no need to run setup_environ
    # we already know our project
    os.environ['DJANGO_SETTINGS_MODULE'] = os.environ.get('DJANGO_SETTINGS_MODULE',
                                                          'synnefo.settings')
    mu = SynnefoManagementUtility(sys.argv)
    mu.execute()

if __name__ == "__main__":
    main()
