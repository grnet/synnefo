# Copyright 2012 GRNET S.A. All rights reserved.
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
from contextlib import contextmanager

from synnefo.settings import (CYCLADES_QUOTAHOLDER_URL, USE_QUOTAHOLDER,
                              VMS_USER_QUOTA, MAX_VMS_PER_USER,
                              NETWORKS_USER_QUOTA, MAX_NETWORKS_PER_USER)

from synnefo.db.models import QuotaHolderSerial, VirtualMachine, Network
from synnefo.api.faults import OverLimit

from kamaki.clients.quotaholder import QuotaholderClient
from synnefo.lib.quotaholder.api import (NoCapacityError, NoQuantityError)
from synnefo.lib.commissioning import CallError

import logging
log = logging.getLogger(__name__)


class DummySerial(QuotaHolderSerial):
    accepted = True
    rejected = True
    pending = True
    id = None

    def save(*args, **kwargs):
        pass


class DummyQuotaholderClient(object):
    def issue_commission(self, **commission_info):
        provisions = commission_info["provisions"]
        userid = commission_info["target"]
        for provision in provisions:
            entity, resource, size = provision
            if resource == "cyclades.vm":
                user_vms = VirtualMachine.objects.filter(userid=userid,
                                                         deleted=False).count()
                user_vm_limit = VMS_USER_QUOTA.get(userid, MAX_VMS_PER_USER)
                log.warning("Users VMs %s User Limits %s", user_vms,
                        user_vm_limit)
                if user_vms + size >= user_vm_limit:
                    raise NoQuantityError()
            if resource == "cyclades.network.private":
                user_networks = Network.objects.filter(userid=userid,
                                                       deleted=False).count()
                user_network_limit = NETWORKS_USER_QUOTA.get(userid,
                                                         MAX_NETWORKS_PER_USER)
                if user_networks + size >= user_network_limit:
                    raise NoQuantityError()

        return None

    def accept_commission(self, *args, **kwargs):
        pass

    def reject_commission(self, *args, **kwargs):
        pass

    def get_pending_commissions(self, *args, **kwargs):
        return []


@contextmanager
def get_quota_holder():
    """Context manager for using a QuotaHolder."""
    if USE_QUOTAHOLDER:
        quotaholder = QuotaholderClient(CYCLADES_QUOTAHOLDER_URL)
    else:
        quotaholder = DummyQuotaholderClient()

    try:
        yield quotaholder
    finally:
        pass


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
            if serials:
                accept_commission(serials)
            return ret
        except CallError:
            log.exception("Unexpected error")
            raise
        except:
            if serials:
                reject_commission(serials=serials)
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

    with get_quota_holder() as qh:
        qh.accept_commission(context={},
                             clientkey='cyclades',
                             serials=[s.serial for s in serials])


def reject_commission(serials, update_db=True):
    """Reject a list of pending commissions.

    @param serials: List of QuotaHolderSerial objects

    """
    if update_db:
        for s in serials:
            if s.pending:
                s.rejected = True
                s.save()

    with get_quota_holder() as qh:
        qh.reject_commission(context={},
                             clientkey='cyclades',
                             serials=[s.serial for s in serials])


def issue_commission(**commission_info):
    """Issue a new commission to the quotaholder.

    Issue a new commission to the quotaholder, and create the
    corresponing QuotaHolderSerial object in DB.

    """

    with get_quota_holder() as qh:
        try:
            serial = qh.issue_commission(**commission_info)
        except (NoCapacityError, NoQuantityError):
            raise OverLimit("Limit exceeded for your account")
        except CallError as e:
            if e.call_error in ["NoCapacityError", "NoQuantityError"]:
                raise OverLimit("Limit exceeded for your account")

    if serial:
        return QuotaHolderSerial.objects.create(serial=serial)
    elif not USE_QUOTAHOLDER:
        return DummySerial()
    else:
        raise Exception("No serial")


# Wrapper functions for issuing commissions for each resource type.  Each
# functions creates the `commission_info` dictionary as expected by the
# `issue_commision` function. Commissions for deleting a resource, are the same
# as for creating the same resource, but with negative resource sizes.


def issue_vm_commission(user, flavor, delete=False):
    resources = get_server_resources(flavor)
    commission_info = create_commission(user, resources, delete)

    return issue_commission(**commission_info)


def get_server_resources(flavor):
    return {'vm': 1,
            'cpu': flavor.cpu,
            'disk': 1073741824 * flavor.disk,  # flavor.disk is in GB
            # 'public_ip': 1,
            #'disk_template': flavor.disk_template,
            'ram': 1048576 * flavor.ram}  # flavor.ram is in MB


def issue_network_commission(user, delete=False):
    resources = get_network_resources()
    commission_info = create_commission(user, resources, delete)

    return issue_commission(**commission_info)


def get_network_resources():
    return {"network.private": 1}


def invert_resources(resources_dict):
    return dict((r, -s) for r, s in resources_dict.items())


def create_commission(user, resources, delete=False):
    if delete:
        resources = invert_resources(resources)
    provisions = [('cyclades', 'cyclades.' + r, s)
                  for r, s in resources.items()]
    return  {"context":    {},
             "target":     user,
             "key":        "1",
             "clientkey":  "cyclades",
             #"owner":      "",
             #"ownerkey":   "1",
             "name":       "",
             "provisions": provisions}

##
## Reconcile pending commissions
##


def accept_commissions(accepted):
    with get_quota_holder() as qh:
        qh.accept_commission(context={},
                             clientkey='cyclades',
                             serials=accepted)


def reject_commissions(rejected):
    with get_quota_holder() as qh:
            qh.reject_commission(context={},
                                 clientkey='cyclades',
                                 serials=rejected)


def fix_pending_commissions():
    (accepted, rejected) = resolve_pending_commissions()

    with get_quota_holder() as qh:
        if accepted:
            qh.accept_commission(context={},
                                 clientkey='cyclades',
                                 serials=accepted)
        if rejected:
            qh.reject_commission(context={},
                                 clientkey='cyclades',
                                 serials=rejected)


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
    with get_quota_holder() as qh:
        pending_serials = qh.get_pending_commissions(context={},
                                                     clientkey='cyclades')
    return pending_serials
