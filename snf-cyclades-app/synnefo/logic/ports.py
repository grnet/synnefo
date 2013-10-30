# Copyright 2011-2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.
from functools import wraps
from django.db import transaction
from synnefo.logic import servers

from logging import getLogger
log = getLogger(__name__)


def port_command(action):
    def decorator(func):
        @wraps(func)
        @transaction.commit_on_success()
        def wrapper(port, *args, **kwargs):
            return func(port, *args, **kwargs)
        return wrapper
    return decorator


@transaction.commit_on_success
def create(network, machine, ipaddress=None, name="", security_groups=None,
           device_owner='vm'):
    """Create a new port connecting a server/router to a network.

    Connect a server/router to a network by creating a new Port. If
    'ipaddress' argument is specified, the port will be assigned this
    IPAddress. Otherwise, an IPv4 address from the IPv4 subnet will be
    allocated.

    """
    port, ipaddress = servers.create_nic(machine, network, ipaddress=ipaddress,
                                         name=name)

    # add the security groups if any
    if security_groups:
        port.security_groups.add(*security_groups)

    machine = servers.connect(machine, network, port)
    jobID = machine.task_job_id

    log.info("Created Port %s with IP Address: %s. Job: %s",
             port, ipaddress, jobID)

    # TODO: Consider quotas for Ports
    # TODO: Associate jobID with the port

    return port


@transaction.commit_on_success
def delete(port):
    """Delete a port by removing the NIC card from the instance.

    Send a Job to remove the NIC card from the instance. The port
    will be deleted and the associated IPv4 addressess will be released
    when the job completes successfully.

    """

    vm = servers.disconnect(port.machine, port)
    log.info("Removing port %s, Job: %s", port, vm.task_job_id)

    return port
