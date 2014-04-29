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

import logging

from django.db import transaction
from django.conf import settings
from snf_django.lib.api import faults
from synnefo.db.models import Volume, VolumeMetadata
from synnefo.volume import util
from synnefo.logic import server_attachments, utils

log = logging.getLogger(__name__)


@transaction.commit_on_success
def create(user_id, size, server_id, name=None, description=None,
           source_volume_id=None, source_snapshot_id=None,
           source_image_id=None, volume_type=None, metadata=None):

    # Currently we cannot create volumes without being attached to a server
    if server_id is None:
        raise faults.BadRequest("Volume must be attached to server")
    server = util.get_server(user_id, server_id, for_update=True,
                             exception=faults.BadRequest)

    # Assert that not more than one source are used
    sources = filter(lambda x: x is not None,
                     [source_volume_id, source_snapshot_id, source_image_id])
    if len(sources) > 1:
        raise faults.BadRequest("Volume can not have more than one source!")

    if source_volume_id is not None:
        source_type = "volume"
        source_uuid = source_volume_id
    elif source_snapshot_id is not None:
        source_type = "snapshot"
        source_uuid = source_snapshot_id
    elif source_image_id is not None:
        source_type = "image"
        source_uuid = source_image_id
    else:
        source_type = "blank"
        source_uuid = None

    volume = _create_volume(server, user_id, size, source_type, source_uuid,
                            name, description, index=None)

    if metadata is not None:
        for meta_key, meta_val in metadata.items():
            utils.check_name_length(meta_key, VolumeMetadata.KEY_LENGTH,
                                    "Metadata key is too long")
            utils.check_name_length(meta_val, VolumeMetadata.VALUE_LENGTH,
                                    "Metadata key is too long")
            volume.metadata.create(key=meta_key, value=meta_val)

    server_attachments.attach_volume(server, volume)

    return volume


def _create_volume(server, user_id, size, source_type, source_uuid,
                   name=None, description=None, index=None,
                   delete_on_termination=True):

    utils.check_name_length(name, Volume.NAME_LENGTH,
                            "Volume name is too long")
    utils.check_name_length(description, Volume.DESCRIPTION_LENGTH,
                            "Volume name is too long")
    # Only ext_ disk template supports cloning from another source. Otherwise
    # is must be the root volume so that 'snf-image' fill the volume
    volume_type = server.flavor.volume_type
    can_have_source = (index == 0 or
                       volume_type.provider in settings.GANETI_CLONE_PROVIDERS)
    if not can_have_source and source_type != "blank":
        msg = ("Cannot specify a 'source' attribute for volume type '%s' with"
               " disk template '%s'" %
               (volume_type.id, volume_type.disk_template))
        raise faults.BadRequest(msg)

    # TODO: Check Volume/Snapshot Status
    if source_type == "volume":
        source_volume = util.get_volume(user_id, source_uuid,
                                        for_update=True,
                                        exception=faults.BadRequest)
        if source_volume.status != "IN_USE":
            raise faults.BadRequest("Cannot clone volume while it is in '%s'"
                                    " status" % source_volume.status)
        # If no size is specified, use the size of the volume
        if size is None:
            size = source_volume.size
        elif size < source_volume.size:
            raise faults.BadRequest("Volume size cannot be smaller than the"
                                    " source volume")
        source = Volume.prefix_source(source_uuid, source_type="volume")
        origin = source_volume.backend_volume_uuid
    elif source_type == "snapshot":
        source_snapshot = util.get_snapshot(user_id, source_uuid,
                                            exception=faults.BadRequest)
        snap_status = source_snapshot.get("status", "").upper()
        if snap_status != "AVAILABLE":
            raise faults.BadRequest("Cannot create volume from snapshot, while"
                                    " snapshot is in '%s' status" %
                                    snap_status)
        source = Volume.prefix_source(source_uuid,
                                      source_type="snapshot")
        if size is None:
            raise faults.BadRequest("Volume size is required")
        elif (size << 30) < int(source_snapshot["size"]):
            raise faults.BadRequest("Volume size '%s' is smaller than"
                                    " snapshot's size '%s'"
                                    % (size << 30, source_snapshot["size"]))
        origin = source_snapshot["mapfile"]
    elif source_type == "image":
        source_image = util.get_image(user_id, source_uuid,
                                      exception=faults.BadRequest)
        img_status = source_image.get("status", "").upper()
        if img_status != "AVAILABLE":
            raise faults.BadRequest("Cannot create volume from image, while"
                                    " image is in '%s' status" % img_status)
        if size is None:
            raise faults.BadRequest("Volume size is required")
        elif (size << 30) < int(source_image["size"]):
            raise faults.BadRequest("Volume size '%s' is smaller than"
                                    " image's size '%s'"
                                    % (size << 30, source_image["size"]))
        source = Volume.prefix_source(source_uuid, source_type="image")
        origin = source_image["mapfile"]
    elif source_type == "blank":
        if size is None:
            raise faults.BadRequest("Volume size is required")
        source = origin = None
    else:
        raise faults.BadRequest("Unknwon source type")

    volume = Volume.objects.create(userid=user_id,
                                   size=size,
                                   volume_type=volume_type,
                                   name=name,
                                   machine=server,
                                   description=description,
                                   delete_on_termination=delete_on_termination,
                                   source=source,
                                   origin=origin,
                                   status="CREATING")
    return volume


@transaction.commit_on_success
def delete(volume):
    """Delete a Volume"""
    # A volume is deleted by detaching it from the server that is attached.
    # Deleting a detached volume is not implemented.
    if volume.machine_id is not None:
        server_attachments.detach_volume(volume.machine, volume)
        log.info("Detach volume '%s' from server '%s', job: %s",
                 volume.id, volume.machine_id, volume.backendjobid)
    else:
        raise faults.BadRequest("Cannot delete a detached volume")

    return volume


@transaction.commit_on_success
def update(volume, name=None, description=None, delete_on_termination=None):
    if name is not None:
        volume.name = name
    if description is not None:
        volume.description = description
    if delete_on_termination is not None:
        volume.delete_on_termination = delete_on_termination

    volume.save()
    return volume
