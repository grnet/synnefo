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
import datetime
from django.utils import importlib

from django.conf import settings
from synnefo.db.models import Backend
from synnefo.logic import backend as backend_mod

log = logging.getLogger(__name__)


class BackendAllocator():
    """Wrapper class for instance allocation.

    """
    def __init__(self):
        self.strategy_mod =\
            importlib.import_module(settings.BACKEND_ALLOCATOR_MODULE)

    def allocate(self, userid, flavor):
        """Allocate a vm of the specified flavor to a backend.

        Warning!!: An explicit commit is required after calling this function,
        in order to release the locks acquired by the get_available_backends
        function.

        """

        backend = None
        backend = get_backend_for_user(userid)
        if backend:
            return backend

        # Get the size of the vm
        disk = flavor_disk(flavor)
        ram = flavor.ram
        cpu = flavor.cpu
        vm = {'ram': ram, 'disk': disk, 'cpu': cpu}

        log.debug("Allocating VM: %r", vm)

        # Get available backends
        available_backends = get_available_backends(flavor)

        if not available_backends:
            return None

        # Find the best backend to host the vm, based on the allocation
        # strategy
        backend = self.strategy_mod.allocate(available_backends, vm)

        log.info("Allocated VM %r, in backend %s", vm, backend)

        # Reduce the free resources of the selected backend by the size of
        # the vm
        reduce_backend_resources(backend, vm)

        return backend


def get_available_backends(flavor):
    """Get the list of available backends that can host a new VM of a flavor.

    The list contains the backends that are online and that have enabled
    the disk_template of the new VM.

    Also, if the new VM will be automatically connected to a public network,
    the backends that do not have an available public IPv4 address are
    excluded.

    """
    disk_template = flavor.volume_type.disk_template
    # Ganeti knows only the 'ext' disk template, but the flavors disk template
    # includes the provider.
    if disk_template.startswith("ext_"):
        disk_template = "ext"

    backends = Backend.objects.select_for_update().filter(offline=False,
                                                          drained=False)
    # Update the disk_templates if there are empty.
    [backend_mod.update_backend_disk_templates(b)
     for b in backends if not b.disk_templates]
    backends = filter(lambda b: disk_template in b.disk_templates,
                      list(backends))

    # Update the backend stats if it is needed
    refresh_backends_stats(backends)

    return backends


def flavor_disk(flavor):
    """ Get flavor's 'real' disk size

    """
    if flavor.volume_type.disk_template == 'drbd':
        return flavor.disk * 1024 * 2
    else:
        return flavor.disk * 1024


def reduce_backend_resources(backend, vm):
    """ Conservatively update the resources of a backend.

    Reduce the free resources of the backend by the size of the of the vm that
    will host. This is an underestimation of the backend capabilities.

    """

    new_mfree = backend.mfree - vm['ram']
    new_dfree = backend.dfree - vm['disk']
    backend.mfree = 0 if new_mfree < 0 else new_mfree
    backend.dfree = 0 if new_dfree < 0 else new_dfree
    backend.pinst_cnt += 1

    backend.save()


def refresh_backends_stats(backends):
    """ Refresh the statistics of the backends.

    Set db backend state to the actual state of the backend, if
    BACKEND_REFRESH_MIN time has passed.

    """

    now = datetime.datetime.now()
    delta = datetime.timedelta(minutes=settings.BACKEND_REFRESH_MIN)
    for b in backends:
        if now > b.updated + delta:
            log.debug("Updating resources of backend %r. Last Updated %r",
                      b, b.updated)
            backend_mod.update_backend_resources(b)


def get_backend_for_user(userid):
    """Find fixed Backend for user based on BACKEND_PER_USER setting."""

    backend = settings.BACKEND_PER_USER.get(userid)

    if not backend:
        return None

    try:
        try:
            backend_id = int(backend)
            return Backend.objects.get(id=backend_id)
        except ValueError:
            pass

        backend_name = str(backend)
        return Backend.objects.get(clustername=backend_name)
    except Backend.DoesNotExist:
        log.error("Invalid backend %s for user %s", backend, userid)
