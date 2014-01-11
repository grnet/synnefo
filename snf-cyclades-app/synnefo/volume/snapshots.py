import logging
from django.utils import simplejson as json
from django.db import transaction
from snf_django.lib.api import faults
from synnefo.plankton.utils import image_backend
from synnefo.logic import backend
from synnefo.volume import util

#import datetime
#from snf_django.lib.api.utils import isoformat

log = logging.getLogger(__name__)

SNAPSHOTS_CONTAINER = "snapshots"
SNAPSHOTS_DOMAIN = "plankton"
SNAPSHOTS_PREFIX = "plankton:"
SNAPSHOTS_TYPE = "application/octet-stream"
SNAPSHOTS_MAPFILE_PREFIX = "archip:"


@transaction.commit_on_success
def create(user_id, volume, name, description, metadata, force=False):
    """Create a snapshot from a given volume

    Create a snapshot from a given volume. The snapshot is first created as
    a file in Pithos, with specified metadata to indicate that it is a
    snapshot. Then a job is sent to Ganeti backend to create the actual
    snapshot of the volume.

    Snapshots are only supported for volumes of ext_ disk template. Also,
    the volume must be attached to some server.

    """

    # Check that taking a snapshot is feasible
    if volume.machine is None:
        raise faults.BadRequest("Cannot snapshot a detached volume!")

    flavor = volume.machine.flavor
    if not flavor.disk_template.startswith("ext_"):
        msg = ("Snapshots are supported only for volumes of ext_*"
               " disk template")
        raise faults.BadRequest(msg)

    # Increase the snapshot counter of the volume that is used in order to
    # generate unique snapshot names
    volume.snapshot_counter += 1
    volume.save()
    transaction.commit()

    # Snapshot information are stored as metadata on the Pithos file
    snapshot_metadata = {
        SNAPSHOTS_PREFIX + "name": name,
        SNAPSHOTS_PREFIX + "description": description,
        SNAPSHOTS_PREFIX + "volume_id": volume.id,
        SNAPSHOTS_PREFIX + "status": "CREATING",
    }

    # TODO: The following are used in order plankton to work with snapshots
    # exactly as with iamges
    snapshot_metadata.update({
        SNAPSHOTS_PREFIX + "store": "pithos",
        SNAPSHOTS_PREFIX + "disk_format": "diskdump",
        SNAPSHOTS_PREFIX + "default_container_format": "bare",
        SNAPSHOTS_PREFIX + "metadata": json.dumps(metadata)})

    # Set a special attribute to distinquish snapshots from the images
    snapshot_metadata[SNAPSHOTS_PREFIX + "is_snapshot"] = True

    # Snapshots are used as images. We set the most important properties
    # that are being used for images. We set 'EXCLUDE_ALL_TASKS' to bypass
    # image customization. Also, we get some basic metadata for the volume from
    # the server that the volume is attached
    image_properties = {"EXCLUDE_ALL_TASKS": "yes",
                        "description": description}
    vm_metadata = dict(volume.machine.metadata
                                     .values_list("meta_key", "meta_value"))
    for key in ["OS", "users"]:
        val = vm_metadata.get(key)
        if val is not None:
            image_properties[key] = val
    snapshot_metadata[SNAPSHOTS_PREFIX + "properties"] = \
        json.dumps(image_properties)

    # Generate a name for the Pithos file. Also, generate a name for the
    # Archipelago mapfile.
    snapshot_pithos_name = generate_snapshot_pithos_name(volume)
    mapfile = SNAPSHOTS_MAPFILE_PREFIX + snapshot_pithos_name

    # Convert size from Gbytes to bytes
    size = volume.size << 30

    with image_backend(user_id) as pithos_backend:
        # move this to plankton backend
        snapshot_uuid = pithos_backend.backend.register_object_map(
            user=user_id,
            account=user_id,
            container=SNAPSHOTS_CONTAINER,
            name=snapshot_pithos_name,
            size=size,
            domain=SNAPSHOTS_DOMAIN,
            type=SNAPSHOTS_TYPE,
            mapfile=mapfile,
            meta=snapshot_metadata,
            replace_meta=True,
            permissions=None)
            #checksum=None,

    backend.snapshot_instance(volume.machine,
                              snapshot_name=snapshot_pithos_name)

    snapshot = util.get_snapshot(user_id, snapshot_uuid)

    return snapshot


def generate_snapshot_pithos_name(volume):
    """Helper function to generate a name for the Pithos file."""
    # time = isoformat(datetime.datetime.now())
    return "snapshot-of-volume-%s-%s" % (volume.id,
                                         volume.snapshot_counter)


@transaction.commit_on_success
def delete(snapshot):
    """Delete a snapshot.

    Delete a snapshot by deleting the corresponding file from Pithos.

    """
    user_id = snapshot["owner"]
    log.info("Deleting snapshot '%s'", snapshot["location"])
    with image_backend(user_id) as pithos_backend:
        pithos_backend.delete_snapshot(snapshot["uuid"])
    return snapshot


def rename(snapshot, new_name):
    # user_id = snapshot["owner"]
    raise NotImplemented("Renaming a snapshot is not implemented!")


def update_description(snapshot, new_description):
    # user_id = snapshot["owner"]
    raise NotImplemented("Updating snapshot's description is not implemented!")
