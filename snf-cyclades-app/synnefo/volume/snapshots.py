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
import simplejson as json
from synnefo.db import transaction
from snf_django.lib.api import faults
from synnefo.plankton.backend import PlanktonBackend, OBJECT_ERROR
from synnefo.logic import backend
from synnefo.volume import util
from synnefo.util import units

log = logging.getLogger(__name__)


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
        "name": name,
        "disk_format": "diskdump",
        "container_format": "bare",
        # Snapshot specific
        "description": description,
        "volume_id": volume.id,
    }

    # Snapshots are used as images. We set the most important properties
    # that are being used for images. We set 'EXCLUDE_ALL_TASKS' to bypass
    # image customization. Also, we get some basic metadata for the volume from
    # the server that the volume is attached
    metadata.update({"exclude_all_tasks": "yes",
                     "description": description})
    if volume.index == 0:
        # Copy the metadata of the VM into the image properties only when the
        # volume is the root volume of the VM.
        vm_metadata = dict(volume.machine.metadata
                                         .filter(meta_key__in=["OS", "users"])
                                         .values_list("meta_key",
                                                      "meta_value"))
        metadata.update(vm_metadata)

    snapshot_properties = PlanktonBackend._prefix_properties(metadata)
    snapshot_metadata.update(snapshot_properties)

    # Generate a name for the Archipelago mapfile.
    mapfile = generate_mapfile_name(volume)

    # Convert size from Gbytes to bytes
    size = volume.size << 30

    with PlanktonBackend(user_id) as b:
        try:
            snapshot_id = b.register_snapshot(name=name,
                                              mapfile=mapfile,
                                              size=size,
                                              metadata=snapshot_metadata)
        except faults.OverLimit:
            msg = ("Resource limit exceeded for your account."
                   " Not enough storage space to create snapshot of"
                   " %s size." % units.show(size, "bytes", "gb"))
            raise faults.OverLimit(msg)

        try:
            job_id = backend.snapshot_instance(volume.machine, volume,
                                               snapshot_name=mapfile,
                                               snapshot_id=snapshot_id)
        except:
            # If failed to enqueue job to Ganeti, mark snapshot as ERROR
            b.update_snapshot_state(snapshot_id, OBJECT_ERROR)
            raise

        # Store the backend and job id as metadata in the snapshot in order
        # to make reconciliation based on the Ganeti job possible.
        backend_info = {
            "ganeti_job_id": job_id,
            "ganeti_backend_id": volume.machine.backend_id
        }
        metadata = {"backend_info": json.dumps(backend_info)}
        b.update_metadata(snapshot_id, metadata)

    snapshot = util.get_snapshot(user_id, snapshot_id)

    return snapshot


def generate_mapfile_name(volume):
    """Helper function to generate a name for the Archipelago mapfile."""
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
