# Copyright 2012 GRNET S.A. All rights reserved.
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
from django.core.exceptions import PermissionDenied
from django.db import transaction

from astakos.im.models import ProjectApplication
from astakos.im.functions import deny_application

class Command(BaseCommand):
    args = "<project application id>"
    help = """
    Deny a project application

    You can discover projects with a pending application with
    (the last column <AppID> is the application to be denied):

        snf-manage project-list --pending

    You can examine a specific application with:

        snf-manage project-show --app <AppId>

    For a given project, you can examine a pending application with:

        snf-manage project-show <project> --pending
"""

    @transaction.commit_on_success
    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError("Please provide an application identifier")
        try:
            app_id = int(args[0])
        except ValueError:
            raise CommandError('Invalid id')
        else:
            try:
                deny_application(app_id)
            except (PermissionDenied, IOError):
                raise CommandError('Invalid id')
