import logging

from django.db import transaction
from synnefo.db.models import Volume
from snf_django.lib.api import faults
from synnefo.volume import util
from synnefo.logic import backend

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

    source_volume = None
    if source_volume_id is not None:
        source_volume = util.get_volume(user_id, source_volume_id,
                                        for_update=True,
                                        exception=faults.BadRequest)
    source_snapshot = None
    if source_snapshot_id is not None:
        source_snapshot = util.get_snapshot(user_id, source_snapshot_id,
                                            exception=faults.BadRequest)
    source_image = None
    if source_image_id is not None:
        source_image = util.get_image(user_id, source_image_id,
                                      exception=faults.BadRequest)

    volume = Volume.objects.create(userid=user_id,
                                   size=size,
                                   name=name,
                                   machine=server,
                                   description=description,
                                   source_volume=source_volume,
                                   source_image_id=source_image_id,
                                   source_snapshot_id=source_snapshot_id,
                                   #volume_type=volume_type,
                                   status="CREATING")

    if metadata is not None:
        for meta_key, meta_val in metadata.items():
            volume.metadata.create(key=meta_key, value=meta_val)

    # Annote volume with snapshot/image information
    volume.source_snapshot = source_snapshot
    volume.source_image = source_image

    # Create the disk in the backend
    volume.backendjobid = backend.attach_volume(server, volume)
    volume.save()

    return volume


@transaction.commit_on_success
def delete(volume):
    if volume.machine_id is not None:
        raise faults.BadRequest("Volume %s is still in use by server %s"
                                % (volume.id, volume.machine_id))
    volume.deleted = True
    volume.save()

    log.info("Deleted volume %s", volume)

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
