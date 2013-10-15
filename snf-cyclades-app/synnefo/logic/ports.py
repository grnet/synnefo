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
import ipaddr

from functools import wraps
from django.db import transaction

from django.conf import settings
from snf_django.lib.api import faults
from synnefo.api import util
from synnefo import quotas
from synnefo.db.models import NetworkInterface, IPAddress

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
def create(network, machine, name="", security_groups=None,
           device_owner='vm'):

    if network.state != 'ACTIVE':
        raise faults.Conflict('Network build in process')

    #create the port
    port = NetworkInterface.objects.create(name=name,
                                           network=network,
                                           machine=machine,
                                           userid=machine.userid,
                                           device_owner=device_owner,
                                           state="BUILDING")
    #add the security groups if any
    if security_groups:
        port.security_groups.add(*security_groups)

    #add new port to every subnet of the network
    for subn in network.subnets.all():
        IPAddress.objects.create(subnet=subn,
                                 network=network,
                                 nic=port,
                                 userid=machine.userid,
                                 # FIXME
                                 address="192.168.0." + str(subn.id))

    # Issue commission to Quotaholder and accept it since at the end of
    # this transaction the Network object will be created in the DB.
    # Note: the following call does a commit!
    #quotas.issue_and_accept_commission(new_port)

    return port

@transaction.commit_on_success
def delete(port):
    port.ips.all().delete()
    port.delete()
