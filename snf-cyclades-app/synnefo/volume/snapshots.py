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

    flavor = volume.machine.flavor
    if not flavor.disk_template.startswith("ext_"):
        msg = ("Snapshots are supported only for volumes of ext_*"
               " disk template")
        raise faults.BadRequest(msg)

    volume.snapshot_counter += 1
    volume.save()
    transaction.commit()

    snapshot_metadata = {}
    snapshot_metadata[SNAPSHOTS_PREFIX + "name"] = name
    snapshot_metadata[SNAPSHOTS_PREFIX + "description"] = description
    snapshot_metadata[SNAPSHOTS_PREFIX + "metadata"] = json.dumps(metadata)
    snapshot_metadata[SNAPSHOTS_PREFIX + "volume_id"] = volume.id
    snapshot_metadata[SNAPSHOTS_PREFIX + "status"] = "CREATING"
    #XXX: just to work
    snapshot_metadata[SNAPSHOTS_PREFIX + "is_snapshot"] = True
    #XXX: for images
    snapshot_metadata[SNAPSHOTS_PREFIX + "store"] = "pithos"
    snapshot_metadata[SNAPSHOTS_PREFIX + "disk_format"] = "diskdump"
    snapshot_metadata[SNAPSHOTS_PREFIX + "default_container_format"] = "bare"
    # XXX: Hack-ish way to clone the metadata
    image_properties = {"EXCLUDE_ALL_TASKS": "yes",
                        "description": description}
    vm_metadata = dict(volume.machine.metadata.values_list("meta_key", "meta_value"))
    for key in ["OS", "users"]:
        val = vm_metadata.get(key)
        if val is not None:
            image_properties[key] = val
    snapshot_metadata[SNAPSHOTS_PREFIX + "properties"] = json.dumps(image_properties)

    snapshot_name = generate_snapshot_name(volume)
    mapfile = SNAPSHOTS_MAPFILE_PREFIX + snapshot_name

    size = volume.size << 30
    with image_backend(user_id) as pithos_backend:
        # move this to plankton backend
        snapshot_uuid = pithos_backend.backend.register_object_map(
            user=user_id,
            account=user_id,
            container=SNAPSHOTS_CONTAINER,
            name=snapshot_name,
            size=size,
            domain=SNAPSHOTS_DOMAIN,
            type=SNAPSHOTS_TYPE,
            mapfile=mapfile,
            meta=snapshot_metadata,
            replace_meta=True,
            permissions=None)
            #checksum=None,

    backend.snapshot_instance(volume.machine, snapshot_name=snapshot_name)

    snapshot = util.get_snapshot(user_id, snapshot_uuid)

    return snapshot


def generate_snapshot_name(volume):
    time = isoformat(datetime.datetime.now())
    return "snf-snapshot-of-volume-%s-%s" % (volume.id,
                                                volume.snapshot_counter)


@transaction.commit_on_success
def delete(snapshot):
    user_id = snapshot["owner"]
    with image_backend(user_id) as pithos_backend:
        pithos_backend.delete_snapshot(snapshot["uuid"])
    return snapshot
