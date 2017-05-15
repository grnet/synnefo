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

from django.core.management.base import CommandError
from django.core.exceptions import ObjectDoesNotExist

from snf_django.management.commands import SynnefoCommand
from snf_django.management.utils import parse_bool
from synnefo.db.models import RescueImage
from synnefo.api import util

from logging import getLogger

import re
import requests

log = getLogger(__name__)


HELP_MSG = "Modify one or more rescue images"

# requests works with http{s}:// prefixed links
url_matcher = '^(http|https)\:\/\/.*$'


class Command(SynnefoCommand):
    output_transaction = True
    help = HELP_MSG
    args = "<rescue_image_id>"

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
            help="Mark the rescue image as default"),
        make_option(
            '--deleted',
            dest='deleted',
            choices=["True", "False"],
            metavar="True|False",
            help="Mark the rescue image as deleted or undeleted")
    )

    def handle(self, *args, **options):

        if len(args) != 1:
            raise CommandError("Please provide a rescue image ID")

        image_id = int(args[0])
        try:
            rescue_image = RescueImage.objects.get(id=image_id)
        except ObjectDoesNotExist:
            raise CommandError("Could not find an active image with id %d" %
                               image_id)

        name = options.get('name')
        location = options.get('location')
        location_type = options.get('location_type')
        os_family = options.get('os_family')
        os = options.get('os')
        target_os_family = options.get('target_os_family')
        target_os = options.get('target_os')
        default = options.get('default')
        deleted = options.get('deleted')

        # If the image is currently in use, it should not be available
        # for modification
        if (location is not None or location_type is not None) and len(
                util.get_vms_using_rescue_image(rescue_image)) > 0:
            raise CommandError("1 or more VMs are currently using "
                               "image %s" % rescue_image.name)

        if location_type is not None:
            rescue_image.location_type = location_type

        if location is not None:
            rescue_image.location = location
            if location_type is None:
                if re.match(url_matcher, location):
                    rescue_image.location_type = RescueImage.FILETYPE_HTTP
                else:
                    rescue_image.location_type = RescueImage.FILETYPE_FILE

        if rescue_image.location_type == RescueImage.FILETYPE_HTTP:
            r = requests.head(rescue_image.location, allow_redirects=True)
            if r.status_code != 200:
                raise CommandError('Link provided for image file '
                                   'returned %d status code' %
                                   r.status_code)

        if name is not None:
            rescue_image.name = name

        if os_family is not None:
            rescue_image.os_family = os_family

        if os is not None:
            rescue_image.os = os

        if target_os_family is not None:
            rescue_image.target_os_family = target_os_family

        if target_os is not None:
            rescue_image.target_os = target_os

        if default is not None:
            default = parse_bool(options.get('default'), strict=True)
            if default is True:
                default_image = RescueImage.objects.filter(deleted=False,
                        is_default=True).first()
                if default_image is not None:
                    log.info('There is already a default image with id %d, '
                             'will make image with id %d default instead' %
                             (default_image.id, rescue_image.id))
                    default_image.is_default = False
                    default_image.save()
            elif rescue_image.is_default:
                raise CommandError('Image %d is marked as default and '
                                   'and therefore can not be unmarked' %
                                   rescue_image.id)

            rescue_image.is_default = default

        if deleted is not None:
            deleted = parse_bool(options.get('deleted'), strict=True)
            rescue_image.deleted = deleted

        rescue_image.save()
