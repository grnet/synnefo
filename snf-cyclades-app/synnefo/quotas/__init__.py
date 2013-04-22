# Copyright 2012, 2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.

from functools import wraps
from django.utils import simplejson as json

from snf_django.lib.api import faults
from synnefo.db.models import QuotaHolderSerial
from synnefo.settings import CYCLADES_USE_QUOTAHOLDER

from synnefo.settings import (CYCLADES_ASTAKOS_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_URL)
from astakosclient import AstakosClient
from astakosclient.errors import AstakosClientException, QuotaLimit

import logging
log = logging.getLogger(__name__)

DEFAULT_SOURCE = 'system'
RESOURCES = [
    "cyclades.vm",
    "cyclades.cpu",
    "cyclades.disk",
    "cyclades.ram",
    "cyclades.network.private"
]


class Quotaholder(object):
    _object = None

    @classmethod
    def get(cls):
        if cls._object is None:
            cls._object = AstakosClient(
                ASTAKOS_URL,
                use_pool=True,
                logger=log)
        return cls._object


def uses_commission(func):
    """Decorator for wrapping functions that needs commission.

    All decorated functions must take as first argument the `serials` list in
    order to extend them with the needed serial numbers, as return by the
    Quotaholder

    On successful competition of the decorated function, all serials are
    accepted to the quotaholder, otherwise they are rejected.

    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            serials = []
            ret = func(serials, *args, **kwargs)
        except:
            log.exception("Unexpected error")
            try:
                if serials:
                    reject_commission(serials=serials)
            except:
                log.exception("Exception while rejecting serials %s", serials)
                raise
            raise

        # func has completed successfully. accept serials
        try:
            if serials:
                accept_commission(serials)
            return ret
        except:
            log.exception("Exception while accepting serials %s", serials)
            raise
    return wrapper


## FIXME: Wrap the following two functions inside transaction ?
def accept_commission(serials, update_db=True):
    """Accept a list of pending commissions.

    @param serials: List of QuotaHolderSerial objects

    """
    if update_db:
        for s in serials:
            if s.pending:
                s.accepted = True
                s.save()

    accept_serials = [s.serial for s in serials]
    qh_resolve_commissions(accept=accept_serials)


def reject_commission(serials, update_db=True):
    """Reject a list of pending commissions.

    @param serials: List of QuotaHolderSerial objects

    """
    if update_db:
        for s in serials:
            if s.pending:
                s.rejected = True
                s.save()

    reject_serials = [s.serial for s in serials]
    qh_resolve_commissions(reject=reject_serials)


def issue_commission(user, source, provisions,
                     force=False, auto_accept=False):
    """Issue a new commission to the quotaholder.

    Issue a new commission to the quotaholder, and create the
    corresponing QuotaHolderSerial object in DB.

    """

    qh = Quotaholder.get()
    try:
        serial = qh.issue_one_commission(ASTAKOS_TOKEN,
                                         user, source, provisions,
                                         force, auto_accept)
    except QuotaLimit as e:
        msg, details = render_overlimit_exception(e)
        raise faults.OverLimit(msg, details=details)
    except AstakosClientException as e:
        log.exception("Unexpected error")
        raise

    if serial:
        return QuotaHolderSerial.objects.create(serial=serial)
    else:
        raise Exception("No serial")


# Wrapper functions for issuing commissions for each resource type.  Each
# functions creates the `commission_info` dictionary as expected by the
# `issue_commision` function. Commissions for deleting a resource, are the same
# as for creating the same resource, but with negative resource sizes.


def issue_vm_commission(user, flavor, delete=False):
    resources = get_server_resources(flavor)
    if delete:
        resources = reverse_quantities(resources)
    return issue_commission(user, DEFAULT_SOURCE, resources)


def get_server_resources(flavor):
    return {'cyclades.vm': 1,
            'cyclades.cpu': flavor.cpu,
            'cyclades.disk': 1073741824 * flavor.disk,  # flavor.disk is in GB
            # 'public_ip': 1,
            #'disk_template': flavor.disk_template,
            'cyclades.ram': 1048576 * flavor.ram}  # flavor.ram is in MB


def issue_network_commission(user, delete=False):
    resources = get_network_resources()
    if delete:
        resources = reverse_quantities(resources)
    return issue_commission(user, DEFAULT_SOURCE, resources)


def get_network_resources():
    return {"cyclades.network.private": 1}


def reverse_quantities(resources):
    return dict((r, -s) for r, s in resources.items())


##
## Reconcile pending commissions
##


def accept_commissions(accepted):
    qh_resolve_commissions(accept=accepted)


def reject_commissions(rejected):
    qh_resolve_commissions(reject=rejected)


def fix_pending_commissions():
    (accepted, rejected) = resolve_pending_commissions()
    qh_resolve_commissions(accepted, rejected)


def qh_resolve_commissions(accept=None, reject=None):
    if accept is None:
        accept = []
    if reject is None:
        reject = []

    qh = Quotaholder.get()
    qh.resolve_commissions(ASTAKOS_TOKEN, accept, reject)


def resolve_pending_commissions():
    """Resolve quotaholder pending commissions.

    Get pending commissions from the quotaholder and resolve them
    to accepted and rejected, according to the state of the
    QuotaHolderSerial DB table. A pending commission in the quotaholder
    can exist in the QuotaHolderSerial table and be either accepted or
    rejected, or can not exist in this table, so it is rejected.

    """

    qh_pending = get_quotaholder_pending()
    if not qh_pending:
        return ([], [])

    qh_pending.sort()
    min_ = qh_pending[0]

    serials = QuotaHolderSerial.objects.filter(serial__gte=min_, pending=False)
    accepted = serials.filter(accepted=True).values_list('serial', flat=True)
    accepted = filter(lambda x: x in qh_pending, accepted)

    rejected = list(set(qh_pending) - set(accepted))

    return (accepted, rejected)


def get_quotaholder_pending():
    qh = Quotaholder.get()
    pending_serials = qh.get_pending_commissions(ASTAKOS_TOKEN)
    return pending_serials


def render_overlimit_exception(e):
    resource_name = {"vm": "Virtual Machine",
                     "cpu": "CPU",
                     "ram": "RAM",
                     "network.private": "Private Network"}
    details = json.loads(e.details)
    data = details['overLimit']['data']
    usage = data["usage"]
    limit = data["limit"]
    available = limit - usage
    provision = data['provision']
    requested = provision['quantity']
    resource = provision['resource']
    res = resource.replace("cyclades.", "", 1)
    try:
        resource = resource_name[res]
    except KeyError:
        resource = res

    msg = "Resource Limit Exceeded for your account."
    details = "Limit for resource '%s' exceeded for your account."\
              " Available: %s, Requested: %s"\
              % (resource, available, requested)
    return msg, details
