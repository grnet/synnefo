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

from optparse import make_option
import requests
import uuid
import re

from django.core.management.base import CommandError

from snf_django.management.commands import SynnefoCommand
from snf_django.management.utils import parse_bool
from synnefo.db.models import RescueImage

from logging import getLogger


log = getLogger(__name__)


HELP_MSG = "Create one or more rescue images"

# requests works with http{s}:// prefixed links
url_matcher = '^(http|https)\:\/\/.*$'


class Command(SynnefoCommand):
    output_transaction = True
    help = HELP_MSG

    option_list = SynnefoCommand.option_list + (
        make_option("-n", "--dry-run", dest="dry_run", action="store_true"),
        make_option(
            '--name',
            dest='name',
            metavar="<Rescue Image Name>",
            help="Name of the rescue image, if none is provided, a unique "
                 "identifier will be used"),
        make_option(
            '--location',
            dest='location',
            metavar="<Rescue Image Location>",
            help="The location of the image (e.g. HTTP link, filepath)"),
        make_option(
            '--location-type',
            dest='location_type',
            metavar="<Rescue Image Location Type>",
            help="Explicit specification of the location type of the image."
                 "If not provided, the system will assume the type"),
        make_option(
            '--os-family',
            dest='os_family',
            metavar="<Rescue Image OS Family>",
            help="Operating System Family (e.g. Linux, Windows, FreeBSD etc"),
        make_option(
            '--os',
            dest='os',
            metavar="<Rescue Image OS>",
            help="Operating System of the Image"),
        make_option(
            '--target-os-family',
            dest='target_os_family',
            metavar="<Rescue Image Target OS Family>",
            help="Operating System Family (e.g. Linux, Windows, FreeBSD etc "
                 "that will be used to determine the proper rescue image "
                 "when a rescue command is issued"),
        make_option(
            '--target-os',
            dest='target_os',
            metavar="<Rescue Image Target OS>",
            help="Operating System of the Image "
                 "that will be used to determine the proper rescue image "
                 "when a rescue command is issued"),
        make_option(
            '--default',
            dest='default',
            choices=["True", "False"],
            metavar="True|False",
            default="False",
            help="Mark the rescue image as default"),
    )

    def handle(self, *args, **options):

        name = options.get('name')
        location = options.get('location')
        location_type = options.get('location_type')
        os_family = options.get('os_family')
        os = options.get('os')
        target_os_family = options.get('target_os_family')
        target_os = options.get('target_os')
        default = options.get('default')

        if default is not None:
            default = parse_bool(default, strict=True)
            if default and RescueImage.objects.filter(
                    is_default=True).count() > 0:
                raise CommandError('There is already a default image')

        if location is None:
            raise CommandError('Location is required')

        if location_type is None:
            if re.match(url_matcher, location):
                location_type = RescueImage.FILETYPE_HTTP
            else:
                location_type = RescueImage.FILETYPE_FILE

        if location_type == RescueImage.FILETYPE_HTTP:
            r = requests.head(location, allow_redirects=True)
            if r.status_code != 200:
                raise CommandError('Link provided for image file returned %d'
                                   'status code' % r.status_code)

        if name is None:
            name = 'rescue-image-%s' % str(uuid.uuid4())

        rescue_image = RescueImage(name=name, location=location,
                                   location_type=location_type,
                                   os_family=os_family, os=os,
                                   target_os_family=target_os_family,
                                   target_os=target_os,
                                   is_default=default, deleted=False)

        rescue_image.save()
