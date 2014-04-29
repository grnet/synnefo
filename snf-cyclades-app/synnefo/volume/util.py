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

from synnefo.db import models
from snf_django.lib.api import faults
from synnefo.api.util import get_image_dict, get_vm
from synnefo.plankton import backend
from synnefo.cyclades_settings import cyclades_services, BASE_HOST
from synnefo.lib import join_urls
from synnefo.lib.services import get_service_path


def get_volume(user_id, volume_id, for_update=False,
               exception=faults.ItemNotFound):
    volumes = models.Volume.objects
    if for_update:
        volumes = volumes.select_for_update()
    try:
        volume_id = int(volume_id)
    except (TypeError, ValueError):
        raise faults.BadRequest("Invalid volume id: %s" % volume_id)
    try:
        return volumes.get(id=volume_id, userid=user_id)
    except models.Volume.DoesNotExist:
        raise exception("Volume %s not found" % volume_id)


def get_snapshot(user_id, snapshot_id, exception=faults.ItemNotFound):
    try:
        with backend.PlanktonBackend(user_id) as b:
            return b.get_snapshot(user_id, snapshot_id)
    except faults.ItemNotFound:
        raise exception("Snapshot %s not found" % snapshot_id)


def get_image(user_id, image_id, exception=faults.ItemNotFound):
    try:
        return get_image_dict(image_id, user_id)
    except faults.ItemNotFound:
        raise exception("Image %s not found" % image_id)


def get_server(user_id, server_id, for_update=False,
               exception=faults.ItemNotFound):
    try:
        server_id = int(server_id)
    except (TypeError, ValueError):
        raise faults.BadRequest("Invalid server id: %s" % server_id)
    try:
        return get_vm(server_id, user_id, for_update=for_update,
                      non_deleted=True, non_suspended=True)
    except faults.ItemNotFound:
        raise exception("Server %s not found" % server_id)


VOLUME_URL = \
    join_urls(BASE_HOST,
              get_service_path(cyclades_services, "volume", version="v2.0"))

VOLUMES_URL = join_urls(VOLUME_URL, "volumes/")
SNAPSHOTS_URL = join_urls(VOLUME_URL, "snapshots/")


def volume_to_links(volume_id):
    href = join_urls(VOLUMES_URL, str(volume_id))
    return [{"rel": rel, "href": href} for rel in ("self", "bookmark")]


def snapshot_to_links(snapshot_id):
    href = join_urls(SNAPSHOTS_URL, str(snapshot_id))
    return [{"rel": rel, "href": href} for rel in ("self", "bookmark")]


def update_snapshot_status(snapshot_id, user_id, status):
    with backend.PlanktonBackend(user_id) as b:
        return b.update_status(snapshot_id, status=status)
