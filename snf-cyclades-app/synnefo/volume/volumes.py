import logging

from django.db import transaction
from synnefo.db.models import Volume
from snf_django.lib.api import faults
from synnefo.volume import util
from synnefo.logic import backend, servers

log = logging.getLogger(__name__)


@transaction.commit_on_success
def create(user_id, size, server_id, name=None, description=None,
           source_volume_id=None, source_snapshot_id=None,
           source_image_id=None, metadata=None):

    if server_id is None:
        raise faults.BadRequest("Volume must be attached to server")
    server = util.get_server(user_id, server_id, for_update=True,
                             exception=faults.BadRequest)

    # Assert that not more than one source are used
    sources = filter(lambda x: x is not None,
                     [source_volume_id, source_snapshot_id, source_image_id])
    if len(sources) > 1:
        raise faults.BadRequest("Volume can not have more than one source!")

    # Only ext_ disk template supports cloning from another source
    disk_template = server.flavor.disk_template
    if not disk_template.startswith("ext_") and sources:
        msg = ("Volumes of '%s' disk template cannot have a source" %
               disk_template)
        raise faults.BadRequest(msg)

    origin = None
    source = None
    if source_volume_id is not None:
        source_volume = util.get_volume(user_id, source_volume_id,
                                        for_update=True,
                                        exception=faults.BadRequest)
        # Check that volume is ready to be snapshotted
        if source_volume.status != "AVAILABLE":
            msg = ("Cannot take a snapshot while snapshot is in '%s' state"
                   % source_volume.status)
            raise faults.BadRequest(msg)
        source = Volume.prefix_source(source_volume_id, source_type="volume")
        origin = source_volume.backend_volume_uuid
    elif source_snapshot_id is not None:
        source_snapshot = util.get_snapshot(user_id, source_snapshot_id,
                                            exception=faults.BadRequest)
        # TODO: Check the state of the snapshot!!
        source = Volume.prefix_source(source_snapshot_id,
                                      source_type="snapshot")
        origin = source_snapshot["checksum"]
    elif source_image_id is not None:
        source_image = util.get_image(user_id, source_image_id,
                                      exception=faults.BadRequest)
        source = Volume.prefix_source(source_image_id, source_type="image")
        origin = source_image["checksum"]

    volume = Volume.objects.create(userid=user_id,
                                   size=size,
                                   name=name,
                                   machine=server,
                                   description=description,
                                   source=source,
                                   origin=origin,
                                   #volume_type=volume_type,
                                   status="CREATING")

    if metadata is not None:
        for meta_key, meta_val in metadata.items():
            volume.metadata.create(key=meta_key, value=meta_val)

    servers.attach_volume(server, volume)

    return volume


@transaction.commit_on_success
def delete(volume):
    """Delete a Volume"""
    # A volume is deleted by detaching it from the server that is attached.
    # Deleting a detached volume is not implemented.
    if volume.machine_id is not None:
        servers.detach_volume(volume.machine, volume)
        log.info("Detach volume '%s' from server '%s', job: %s",
                 volume.id, volume.machine_id, volume.backendjobid)
    else:
        raise faults.BadRequest("Cannot delete a detached volume")

    return volume


@transaction.commit_on_success
def rename(volume, new_name):
    volume.name = new_name
    volume.save()
    return volume


@transaction.commit_on_success
def update_description(volume, new_description):
    volume.description = new_description
    volume.save()
    return volume
