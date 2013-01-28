# Copyright 2011 GRNET S.A. All rights reserved.
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

"""
Extented django management module

Most of the code is shared from django.core.management module
to allow us extend the default django ManagementUtility object
used to provide command line interface of the django project
included in snf-webproject package.

The extended class provides the following:

- additional argument for the configuration of the SYNNEFO_SETTINGS_DIR
  environmental variable (--settings-dir).
- a fix for management utility to handle custom commands defined in
  applications living in namespaced packages (django ticket #14087)
- override of --version command to display the snf-webproject version
"""

from django.core.management import ManagementUtility, setup_environ, \
BaseCommand, LaxOptionParser, handle_default_options, find_commands, \
load_command_class

from django.core import management
from django.utils.importlib import import_module
from optparse import Option, make_option
from synnefo.util.version import get_component_version
from synnefo.lib.dictconfig import dictConfig

import sys
import locale
import os
import imp

_commands = None


def find_modules(name, path=None):
    """Find all modules with name 'name'

    Unlike find_module in the imp package this returns a list of all
    matched modules.
    """

    results = []
    if path is None: path = sys.path
    for p in path:
        importer = sys.path_importer_cache.get(p, None)
        if importer is None:
            find_module = imp.find_module
        else:
            find_module = importer.find_module

        try:
            result = find_module(name, [p])
            if result is not None:
                results.append(result)
        except ImportError:
            if sys.modules.get(name, None):
                modpath = sys.modules[name].__path__
                if isinstance(modpath, basestring) and not ('', modpath) in results:
                    results.append(('', sys.modules[name].__path__))
                else:
                    for mp in modpath:
                        if not ('', mp) in results:
                            results.append(('', mp))
            pass

    if not results:
        raise ImportError("No module named %.200s" % name)

    return results

def find_management_module(app_name):
    """
    Determines the path to the management module for the given app_name,
    without actually importing the application or the management module.

    Raises ImportError if the management module cannot be found for any reason.
    """
    parts = app_name.split('.')
    parts.append('management')
    parts.reverse()
    part = parts.pop()
    paths = None

    # When using manage.py, the project module is added to the path,
    # loaded, then removed from the path. This means that
    # testproject.testapp.models can be loaded in future, even if
    # testproject isn't in the path. When looking for the management
    # module, we need look for the case where the project name is part
    # of the app_name but the project directory itself isn't on the path.
    try:
        modules = find_modules(part, paths)
        paths = [m[1] for m in modules]
    except ImportError,e:
        if os.path.basename(os.getcwd()) != part:
            raise e

    while parts:
        part = parts.pop()
        modules = find_modules(part, paths)
        paths = [m[1] for m in modules]
    return paths[0]


def get_commands():
    """
    Returns a dictionary mapping command names to their callback applications.

    This works by looking for a management.commands package in django.core, and
    in each installed application -- if a commands package exists, all commands
    in that package are registered.

    Core commands are always included. If a settings module has been
    specified, user-defined commands will also be included, the
    startproject command will be disabled, and the startapp command
    will be modified to use the directory in which the settings module appears.

    The dictionary is in the format {command_name: app_name}. Key-value
    pairs from this dictionary can then be used in calls to
    load_command_class(app_name, command_name)

    If a specific version of a command must be loaded (e.g., with the
    startapp command), the instantiated module can be placed in the
    dictionary in place of the application name.

    The dictionary is cached on the first call and reused on subsequent
    calls.
    """
    global _commands
    if _commands is None:
        _commands = dict([(name, 'django.core') for name in \
            find_commands(management.__path__[0])])

        # Find the installed apps
        try:
            from django.conf import settings
            apps = settings.INSTALLED_APPS
        except (AttributeError, EnvironmentError, ImportError):
            apps = []

        # Find the project directory
        try:
            from django.conf import settings
            module = import_module(settings.SETTINGS_MODULE)
            project_directory = setup_environ(module, settings.SETTINGS_MODULE)
        except (AttributeError, EnvironmentError, ImportError, KeyError):
            project_directory = None

        # Find and load the management module for each installed app.
        for app_name in apps:
            try:
                path = find_management_module(app_name)
                _commands.update(dict([(name, app_name)
                                       for name in find_commands(path)]))
            except ImportError:
                pass # No management module - ignore this app

        if project_directory:
            # Remove the "startproject" command from self.commands, because
            # that's a django-admin.py command, not a manage.py command.
            del _commands['startproject']

            # Override the startapp command so that it always uses the
            # project_directory, not the current working directory
            # (which is default).
            from django.core.management.commands.startapp import ProjectCommand
            _commands['startapp'] = ProjectCommand(project_directory)

    return _commands

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

        # Encode stdout. This check is required because of the way python
        # checks if something is tty: https://bugzilla.redhat.com/show_bug.cgi?id=841152
        if not 'shell' in subcommand:
            sys.stdout = EncodedStdOut(sys.stdout)

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

    def main_help_text(self):
        """
        Returns the script's main help text, as a string.
        """
        usage = ['',"Type '%s help <subcommand>' for help on a specific subcommand." % self.prog_name,'']
        usage.append('Available subcommands:')
        commands = get_commands().keys()
        commands.sort()
        for cmd in commands:
            usage.append('  %s' % cmd)
        return '\n'.join(usage)

    def fetch_command(self, subcommand):
        """
        Tries to fetch the given subcommand, printing a message with the
        appropriate command called from the command line (usually
        "django-admin.py" or "manage.py") if it can't be found.
        """
        try:
            app_name = get_commands()[subcommand]
        except KeyError:
            sys.stderr.write("Unknown command: %r\nType '%s help' for usage.\n" % \
                (subcommand, self.prog_name))
            sys.exit(1)
        if isinstance(app_name, BaseCommand):
            # If the command is already loaded, use it directly.
            klass = app_name
        else:
            klass = load_command_class(app_name, subcommand)
        return klass


def configure_logging():
    try:
        from synnefo.settings import SNF_MANAGE_LOGGING_SETUP
        dictConfig(SNF_MANAGE_LOGGING_SETUP)
    except ImportError:
        import logging
        logging.basicConfig()
        log = logging.getLogger()
        log.warning("SNF_MANAGE_LOGGING_SETUP setting missing.")


class EncodedStdOut(object):
    def __init__(self, stdout):
        try:
            std_encoding = stdout.encoding
        except AttributeError:
            std_encoding = None
        self.encoding = std_encoding or locale.getpreferredencoding()
        self.original_stdout = stdout

    def write(self, string):
        if isinstance(string, unicode):
            string = string.encode(self.encoding)
        self.original_stdout.write(string)

    def __getattr__(self, name):
        return getattr(self.original_stdout, name)


def main():
    # no need to run setup_environ
    # we already know our project
    os.environ['DJANGO_SETTINGS_MODULE'] = os.environ.get('DJANGO_SETTINGS_MODULE',
                                                          'synnefo.settings')
    configure_logging()
    mu = SynnefoManagementUtility(sys.argv)
    mu.execute()

if __name__ == "__main__":
    main()
