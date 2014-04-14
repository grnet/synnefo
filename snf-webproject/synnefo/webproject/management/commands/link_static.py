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
"""
Collect static files required by synnefo to a specific location
"""
import os

from django.utils.importlib import import_module
from optparse import make_option
from django.conf import settings

from snf_django.management.commands import SynnefoCommand

STATIC_FILES = getattr(settings, "STATIC_FILES", {})


class Command(SynnefoCommand):

    help = 'Symlink static files to directory specified'

    option_list = SynnefoCommand.option_list + (
        make_option(
            '--static-root',
            action='store',
            dest='static_root',
            default=settings.MEDIA_ROOT,
            help='Path to place symlinks (default: `%s`)'
                 % settings.MEDIA_ROOT),
        make_option(
            '--dry-run',
            action='store_true',
            dest='dry',
            default=False,
            help='Do not actually create symlinks'),
        )

    def collect_files(self, target):
        symlinks = []
        for module, ns in STATIC_FILES.iteritems():
            module = import_module(module)
            static_root = os.path.join(os.path.dirname(module.__file__),
                                       'static')

            # no nested dir exists for the app
            if ns == '':
                for f in os.listdir(static_root):
                    symlinks.append((os.path.join(static_root, f),
                                     os.path.join(target, ns, f)))

            # symlink whole app directory
            else:
                symlinks.append((os.path.join(static_root),
                                 os.path.join(target, ns)))

        return symlinks

    def handle(self, *args, **options):

        self.stderr.write("The following symlinks will be created\n")

        symlinks = self.collect_files(options['static_root'])
        for linkfrom, linkto in symlinks:
            self.stderr.write("Symlink '%s' to '%s' will be created.\n"
                              % (linkfrom, linkto))

        if not options['dry']:
            confirm = raw_input("""
Are you soure you want to continue ?
Type 'yes' to continue, or 'no' to cancel: """)

            if confirm == "yes":
                for linkfrom, linkto in symlinks:
                    self.stderr.write("Creating link from %s to %s\n"
                                      % (linkfrom, linkto))
                    if os.path.exists(linkto):
                        self.stderr.write("Skippig %s\n" % linkto)
                        continue

                    os.symlink(linkfrom, linkto)
