# Copyright 2011 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.
"""
Collect static files required by synnefo to a specific location
"""
import os, shutil

from django.utils.importlib import import_module
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

STATIC_FILES = getattr(settings, "STATIC_FILES", {})

class Command(BaseCommand):

    help = 'Symlink static files to directory specified'

    option_list = BaseCommand.option_list + (
        make_option('--static-root',
            action='store',
            dest='static_root',
            default=settings.MEDIA_ROOT,
            help='Path to place symlinks (default: `%s`)' % settings.MEDIA_ROOT),
        make_option('--dry-run',
            action='store_true',
            dest='dry',
            default=False,
            help='Do not actually create symlinks'),
        )

    def collect_files(self, target):
        symlinks = []
        dirs_to_create = set()
        for module, ns in STATIC_FILES.iteritems():
            module = import_module(module)
            static_root = os.path.join(os.path.dirname(module.__file__), 'static')

            # no nested dir exists for the app
            if ns == '':
                for f in os.listdir(static_root):
                    symlinks.append((os.path.join(static_root, f), os.path.join(target, ns, f)))

            # symlink whole app directory
            else:
                symlinks.append((os.path.join(static_root), os.path.join(target, ns)))

        return symlinks

    def handle(self, *args, **options):

        print "The following synlinks will get created"

        symlinks = self.collect_files(options['static_root'])
        for linkfrom, linkto in symlinks:
            print "Symlink '%s' to '%s' will get created." % (linkfrom, linkto)

        if not options['dry']:
            confirm = raw_input("""
Are you soure you want to continue ?
Type 'yes' to continue, or 'no' to cancel: """)

            if confirm == "yes":
                for linkfrom, linkto in symlinks:
                    print "Creating link from %s to %s" % (linkfrom, linkto)
                    if os.path.exists(linkto):
                        print "Skippig %s" % linkto
                        continue

                    os.symlink(linkfrom, linkto)

