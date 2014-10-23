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

from synnefo.db import transaction
from django.conf import settings
from snf_django.lib.api import faults
from synnefo.db.models import Volume, VolumeMetadata
from synnefo.volume import util
from synnefo.logic import server_attachments, utils, commands
from synnefo.plankton.backend import OBJECT_AVAILABLE
from synnefo import quotas

log = logging.getLogger(__name__)


@transaction.commit_on_success
def create(user_id, size, server_id, name=None, description=None,
           source_volume_id=None, source_snapshot_id=None,
           source_image_id=None, volume_type_id=None, metadata=None,
           project=None):

    # Currently we cannot create volumes without being attached to a server
    if server_id is None:
        raise faults.BadRequest("Volume must be attached to server")
    server = util.get_server(user_id, server_id, for_update=True,
                             non_deleted=True,
                             exception=faults.BadRequest)

    server_vtype = server.flavor.volume_type
    if volume_type_id is not None:
        volume_type = util.get_volume_type(volume_type_id,
                                           include_deleted=False,
                                           exception=faults.BadRequest)
        if volume_type != server_vtype:
            raise faults.BadRequest("Cannot create a volume with type '%s' to"
                                    " a server with volume type '%s'."
                                    % (volume_type.id, server_vtype.id))
    else:
        volume_type = server_vtype

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

    if project is None:
        project = user_id

    if metadata is not None and \
       len(metadata) > settings.CYCLADES_VOLUME_MAX_METADATA:
        raise faults.BadRequest("Volumes cannot have more than %s metadata "
                                "items" %
                                settings.CYCLADES_VOLUME_MAX_METADATA)

    volume = _create_volume(server, user_id, project, size,
                            source_type, source_uuid,
                            volume_type=volume_type, name=name,
                            description=description, index=None)

    if metadata is not None:
        for meta_key, meta_val in metadata.items():
            utils.check_name_length(meta_key, VolumeMetadata.KEY_LENGTH,
                                    "Metadata key is too long")
            utils.check_name_length(meta_val, VolumeMetadata.VALUE_LENGTH,
                                    "Metadata key is too long")
            volume.metadata.create(key=meta_key, value=meta_val)

    server_attachments.attach_volume(server, volume)

    return volume


def _create_volume(server, user_id, project, size, source_type, source_uuid,
                   volume_type, name=None, description=None, index=None,
                   delete_on_termination=True):

    utils.check_name_length(name, Volume.NAME_LENGTH,
                            "Volume name is too long")
    utils.check_name_length(description, Volume.DESCRIPTION_LENGTH,
                            "Volume description is too long")
    validate_volume_termination(volume_type, delete_on_termination)

    if index is None:
        # Counting a server's volumes is safe, because we have an
        # X-lock on the server.
        index = server.volumes.filter(deleted=False).count()

    if size is not None:
        try:
            size = int(size)
        except (TypeError, ValueError):
            raise faults.BadRequest("Volume 'size' needs to be a positive"
                                    " integer value.")
        if size < 1:
            raise faults.BadRequest("Volume size must be a positive integer")
        if size > settings.CYCLADES_VOLUME_MAX_SIZE:
            raise faults.BadRequest("Maximum volume size is '%sGB'" %
                                    settings.CYCLADES_VOLUME_MAX_SIZE)

    # Only ext_ disk template supports cloning from another source. Otherwise
    # is must be the root volume so that 'snf-image' fill the volume
    can_have_source = (index == 0 or
                       volume_type.provider in settings.GANETI_CLONE_PROVIDERS)
    if not can_have_source and source_type != "blank":
        msg = ("Cannot specify a 'source' attribute for volume type '%s' with"
               " disk template '%s'" %
               (volume_type.id, volume_type.disk_template))
        raise faults.BadRequest(msg)

    source_version = None
    origin_size = None
    # TODO: Check Volume/Snapshot Status
    if source_type == "snapshot":
        source_snapshot = util.get_snapshot(user_id, source_uuid,
                                            exception=faults.BadRequest)
        snap_status = source_snapshot.get("status", "").upper()
        if snap_status != OBJECT_AVAILABLE:
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
        source_version = source_snapshot["version"]
        origin = source_snapshot["mapfile"]
        origin_size = source_snapshot["size"]
    elif source_type == "image":
        source_image = util.get_image(user_id, source_uuid,
                                      exception=faults.BadRequest)
        img_status = source_image.get("status", "").upper()
        if img_status != OBJECT_AVAILABLE:
            raise faults.BadRequest("Cannot create volume from image, while"
                                    " image is in '%s' status" % img_status)
        if size is None:
            raise faults.BadRequest("Volume size is required")
        elif (size << 30) < int(source_image["size"]):
            raise faults.BadRequest("Volume size '%s' is smaller than"
                                    " image's size '%s'"
                                    % (size << 30, source_image["size"]))
        source = Volume.prefix_source(source_uuid, source_type="image")
        source_version = source_image["version"]
        origin = source_image["mapfile"]
        origin_size = source_image["size"]
    elif source_type == "blank":
        if size is None:
            raise faults.BadRequest("Volume size is required")
        source = origin = None
    elif source_type == "volume":
        # Currently, Archipelago does not support cloning a volume
        raise faults.BadRequest("Cloning a volume is not supported")
        # source_volume = util.get_volume(user_id, source_uuid,
        #                                 for_update=True, non_deleted=True,
        #                                 exception=faults.BadRequest)
        # if source_volume.status != "IN_USE":
        #     raise faults.BadRequest("Cannot clone volume while it is in '%s'"
        #                             " status" % source_volume.status)
        # # If no size is specified, use the size of the volume
        # if size is None:
        #     size = source_volume.size
        # elif size < source_volume.size:
        #     raise faults.BadRequest("Volume size cannot be smaller than the"
        #                             " source volume")
        # source = Volume.prefix_source(source_uuid, source_type="volume")
        # origin = source_volume.backend_volume_uuid
    else:
        raise faults.BadRequest("Unknown source type")

    volume = Volume.objects.create(userid=user_id,
                                   project=project,
                                   size=size,
                                   volume_type=volume_type,
                                   name=name,
                                   machine=server,
                                   description=description,
                                   delete_on_termination=delete_on_termination,
                                   source=source,
                                   source_version=source_version,
                                   origin=origin,
                                   index=index,
                                   status="CREATING")

    # Store the size of the origin in the volume object but not in the DB.
    # We will have to change this in order to support detachable volumes.
    volume.origin_size = origin_size

    return volume


@transaction.commit_on_success
def delete(volume):
    """Delete a Volume"""
    # A volume is deleted by detaching it from the server that is attached.
    # Deleting a detached volume is not implemented.
    server_id = volume.machine_id
    if server_id is not None:
        server = util.get_server(volume.userid, server_id, for_update=True,
                                 non_deleted=True,
                                 exception=faults.BadRequest)
        server_attachments.detach_volume(server, volume)
        log.info("Detach volume '%s' from server '%s', job: %s",
                 volume.id, server_id, volume.backendjobid)
    else:
        raise faults.BadRequest("Cannot delete a detached volume")

    return volume


@transaction.commit_on_success
def update(volume, name=None, description=None, delete_on_termination=None):
    if name is not None:
        utils.check_name_length(name, Volume.NAME_LENGTH,
                                "Volume name is too long")
        volume.name = name
    if description is not None:
        utils.check_name_length(description, Volume.DESCRIPTION_LENGTH,
                                "Volume description is too long")
        volume.description = description
    if delete_on_termination is not None:
        validate_volume_termination(volume.volume_type, delete_on_termination)
        volume.delete_on_termination = delete_on_termination

    volume.save()
    return volume


@transaction.commit_on_success
def reassign_volume(volume, project):
    if volume.index == 0:
        raise faults.Conflict("Cannot reassign: %s is a system volume" %
                              volume.id)
    if volume.machine_id is not None:
        server = util.get_server(volume.userid, volume.machine_id,
                                 for_update=True, non_deleted=True,
                                 exception=faults.BadRequest)
        commands.validate_server_action(server, "REASSIGN")
    action_fields = {"from_project": volume.project, "to_project": project}
    log.info("Reassigning volume %s from project %s to %s",
             volume.id, volume.project, project)
    volume.project = project
    volume.save()
    quotas.issue_and_accept_commission(volume, action="REASSIGN",
                                       action_fields=action_fields)


def validate_volume_termination(volume_type, delete_on_termination):
    """Validate volume's termination mode based on volume's type.

    NOTE: Currently, detached volumes are not supported, so all volumes
    must be terminated upon instance deletion.

    """
    if delete_on_termination is False:
        # Only ext_* volumes can be preserved
        if volume_type.template != "ext":
            raise faults.BadRequest("Volumes of '%s' disk template cannot have"
                                    " 'delete_on_termination' attribute set"
                                    " to 'False'" % volume_type.disk_template)
        # But currently all volumes must be terminated
        raise faults.NotImplemented("Volumes with the 'delete_on_termination'"
                                    " attribute set to False are not"
                                    " supported")
