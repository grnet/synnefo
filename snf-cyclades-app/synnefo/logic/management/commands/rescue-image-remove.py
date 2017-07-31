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
from synnefo.db.models import RescueImage
from synnefo.api import util

from logging import getLogger


log = getLogger(__name__)


HELP_MSG = """Delete one or more rescue images.

Delete one or more rescue images (images used for rescuing VMs). If one more
VMs are currently using the image, then this operation will fail. You can
check if an image is valid for deleting by using the
`snf-manage rescue-image-show <image-id>` command
"""


class Command(SynnefoCommand):
    output_transaction = True
    args = "<rescue_image_id>"
    help = HELP_MSG

    option_list = SynnefoCommand.option_list + (
        make_option("-n", "--dry-run",
                    dest="dry_run",
                    action="store_true",
                    help="Do not actually delete the image, can be used to "
                         "check if an image is available for deleting."),
        make_option("-f", "--force",
                    dest="force",
                    action="store_true",
                    help="Force deletion. Use this option very cautiously"))

    def handle(self, *args, **options):

        if len(args) != 1:
            raise CommandError("Please provide a rescue image ID")

        image_id = int(args[0])
        try:
            rescue_image = RescueImage.objects.get(id=image_id, deleted=False)
        except ObjectDoesNotExist:
            raise CommandError("Could not find an active image with id %d" %
                               image_id)

        if rescue_image.is_default:
            raise CommandError("Image %s is marked as default and therefore "
                               "can not be deleted" % rescue_image.name)

        if len(util.get_vms_using_rescue_image(rescue_image)) > 0\
           and options.get('force') is None:
            raise CommandError("1 or more VMs are currently using image %s" %
                               rescue_image.name)

        print('Deleting image %s' % rescue_image.name)
        if options.get('dry_run') is None:
            rescue_image.deleted = True
            rescue_image.save()
