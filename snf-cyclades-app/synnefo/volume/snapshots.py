import datetime
from django.utils import simplejson as json
from django.db import transaction
from snf_django.lib.api import faults
from snf_django.lib.api.utils import isoformat
from synnefo.plankton.utils import image_backend
from synnefo.logic import backend
from synnefo.volume import util


SNAPSHOTS_CONTAINER = "snapshots"
SNAPSHOTS_DOMAIN = "plankton"
SNAPSHOTS_PREFIX = "plankton:"
SNAPSHOTS_TYPE = "application/octet-stream"
SNAPSHOTS_MAPFILE_PREFIX = "archip:"


@transaction.commit_on_success
def create(user_id, volume, name, description, metadata, force=False):

    if volume.machine is None:
        raise faults.BadRequest("Can not snapshot detached volume!")

    volume.snapshot_counter += 1
    volume.save()

    snapshot_metadata = {}
    snapshot_metadata[SNAPSHOTS_PREFIX + "name"] = description
    snapshot_metadata[SNAPSHOTS_PREFIX + "description"] = description
    snapshot_metadata[SNAPSHOTS_PREFIX + "metadata"] = json.dumps(metadata)
    snapshot_metadata[SNAPSHOTS_PREFIX + "volume_id"] = volume.id
    snapshot_metadata[SNAPSHOTS_PREFIX + "status"] = "CREATING"
    #XXX: just to work
    snapshot_metadata[SNAPSHOTS_PREFIX + "is_snapshot"] = True

    snapshot_name = generate_snapshot_name(volume)
    mapfile = SNAPSHOTS_MAPFILE_PREFIX + snapshot_name

    with image_backend(user_id) as pithos_backend:
        # move this to plankton backend
        snapshot_uuid = pithos_backend.backend.register_object_map(
            user=user_id,
            account=user_id,
            container=SNAPSHOTS_CONTAINER,
            name=name,
            size=volume.size,
            type=SNAPSHOTS_TYPE,
            mapfile=mapfile,
            meta=snapshot_metadata,
            replace_meta=False,
            permissions=None)
            #checksum=None,

    backend.snapshot_instance(volume.machine, snapshot_name=snapshot_uuid)

    snapshot = util.get_snapshot(user_id, snapshot_uuid)

    return snapshot


def generate_snapshot_name(volume):
    time = isoformat(datetime.datetime.now())
    return "snf-snapshot-of-volume-%s-%s-%s" % (volume.id,
                                                volume.snapshot_counter, time)


@transaction.commit_on_success
def delete(snapshot):
    user_id = snapshot["owner"]
    with image_backend(user_id) as pithos_backend:
        pithos_backend.delete_snapshot(snapshot["uuid"])
    return snapshot
