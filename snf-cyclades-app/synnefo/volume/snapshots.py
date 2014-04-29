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
from snf_django.lib.api import faults
from synnefo.plankton.backend import PlanktonBackend
from synnefo.logic import backend
from synnefo.volume import util

log = logging.getLogger(__name__)

PLANKTON_DOMAIN = "plankton"
PLANKTON_PREFIX = "plankton:"

PROPERTY_PREFIX = "property:"

SNAPSHOT_PREFIX = "snapshot:"
SNAPSHOTS_CONTAINER = "snapshots"
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

    if name is None:
        raise faults.BadRequest("Snapshot 'name' is required")

    # Check that taking a snapshot is feasible
    if volume.machine is None:
        raise faults.BadRequest("Cannot snapshot a detached volume!")
    if volume.status not in ["AVAILABLE", "IN_USE"]:
        raise faults.BadRequest("Cannot create snapshot while volume is in"
                                " '%s' status" % volume.status)

    volume_type = volume.volume_type
    if not volume_type.disk_template.startswith("ext_"):
        msg = ("Cannot take a snapshot from a volume with volume type '%s' and"
               " '%s' disk template" %
               (volume_type.id, volume_type.disk_template))
        raise faults.BadRequest(msg)

    # Increase the snapshot counter of the volume that is used in order to
    # generate unique snapshot names
    volume.snapshot_counter += 1
    volume.save()
    transaction.commit()

    snapshot_metadata = {
        PLANKTON_PREFIX + "name": name,
        PLANKTON_PREFIX + "status": "CREATING",
        PLANKTON_PREFIX + "disk_format": "diskdump",
        PLANKTON_PREFIX + "container_format": "bare",
        PLANKTON_PREFIX + "is_snapshot": True,
        # Snapshot specific
        PLANKTON_PREFIX + "description": description,
        PLANKTON_PREFIX + "volume_id": volume.id,
    }

    # Snapshots are used as images. We set the most important properties
    # that are being used for images. We set 'EXCLUDE_ALL_TASKS' to bypass
    # image customization. Also, we get some basic metadata for the volume from
    # the server that the volume is attached
    metadata.update({"EXCLUDE_ALL_TASKS": "yes",
                     "description": description})
    vm_metadata = dict(volume.machine.metadata
                                     .filter(meta_key__in=["OS", "users"])
                                     .values_list("meta_key", "meta_value"))
    metadata.update(vm_metadata)

    for key, val in metadata.items():
        snapshot_metadata[PLANKTON_PREFIX + PROPERTY_PREFIX + key] = val

    # Generate a name for the Pithos file. Also, generate a name for the
    # Archipelago mapfile.
    snapshot_pithos_name = generate_snapshot_pithos_name(volume)
    mapfile = SNAPSHOTS_MAPFILE_PREFIX + snapshot_pithos_name

    # Convert size from Gbytes to bytes
    size = volume.size << 30

    with PlanktonBackend(user_id) as pithos_backend:
        # move this to plankton backend
        snapshot_id = pithos_backend.backend.register_object_map(
            user=user_id,
            account=user_id,
            container=SNAPSHOTS_CONTAINER,
            name=snapshot_pithos_name,
            size=size,
            domain=PLANKTON_DOMAIN,
            type=SNAPSHOTS_TYPE,
            mapfile=mapfile,
            meta=snapshot_metadata,
            replace_meta=True,
            permissions=None)

    backend.snapshot_instance(volume.machine,
                              snapshot_name=snapshot_pithos_name,
                              snapshot_id=snapshot_id)

    snapshot = util.get_snapshot(user_id, snapshot_id)

    return snapshot


def generate_snapshot_pithos_name(volume):
    """Helper function to generate a name for the Pithos file."""
    # time = isoformat(datetime.datetime.now())
    return "snf-snap-%s-%s" % (volume.id,
                               volume.snapshot_counter)


@transaction.commit_on_success
def delete(snapshot):
    """Delete a snapshot.

    Delete a snapshot by deleting the corresponding file from Pithos.

    """
    user_id = snapshot["owner"]
    log.info("Deleting snapshot '%s'", snapshot["location"])
    with PlanktonBackend(user_id) as pithos_backend:
        pithos_backend.delete_snapshot(snapshot["id"])
    return snapshot


def update(snapshot, name=None, description=None):
    """Update a snapshot

    Update the name or description of a snapshot.
    """
    metadata = {}
    if name is not None:
        metadata["name"] = name
    if description is not None:
        metadata["description"] = description
    if not metadata:
        return
    user_id = snapshot["owner"]
    with PlanktonBackend(user_id) as b:
        return b.update_metadata(snapshot["id"], metadata)
