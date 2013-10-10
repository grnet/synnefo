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

from django.utils import simplejson as json
from django.db import transaction

from snf_django.lib.api import faults
from synnefo.db.models import (QuotaHolderSerial, VirtualMachine, Network,
                               IPAddress)

from synnefo.settings import (CYCLADES_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_AUTH_URL)
from astakosclient import AstakosClient
from astakosclient import errors

import logging
log = logging.getLogger(__name__)


DEFAULT_SOURCE = 'system'
RESOURCES = [
    "cyclades.vm",
    "cyclades.cpu",
    "cyclades.active_cpu",
    "cyclades.disk",
    "cyclades.ram",
    "cyclades.active_ram",
    "cyclades.network.private",
    "cyclades.floating_ip",
]


class Quotaholder(object):
    _object = None

    @classmethod
    def get(cls):
        if cls._object is None:
            cls._object = AstakosClient(ASTAKOS_TOKEN,
                                        ASTAKOS_AUTH_URL,
                                        use_pool=True,
                                        retry=3,
                                        logger=log)
        return cls._object


class AstakosClientExceptionHandler(object):
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        pass

    def __exit__(self, exc_type, value, traceback):
        if value is not None:  # exception
            if not isinstance(value, errors.AstakosClientException):
                return False  # reraise
            if exc_type is errors.QuotaLimit:
                msg, details = render_overlimit_exception(value)
                raise faults.OverLimit(msg, details=details)

            log.exception("Unexpected error %s" % value.message)
            raise faults.InternalServerError("Unexpected error")


def issue_commission(resource, action, name="", force=False, auto_accept=False,
                     action_fields=None):
    """Issue a new commission to the quotaholder.

    Issue a new commission to the quotaholder, and create the
    corresponing QuotaHolderSerial object in DB.

    """

    provisions = get_commission_info(resource=resource, action=action,
                                     action_fields=action_fields)

    if provisions is None:
        return None

    user = resource.userid
    source = DEFAULT_SOURCE

    qh = Quotaholder.get()
    if True:  # placeholder
        with AstakosClientExceptionHandler():
            serial = qh.issue_one_commission(user, source,
                                             provisions, name=name,
                                             force=force,
                                             auto_accept=auto_accept)

    if serial:
        serial_info = {"serial": serial}
        if auto_accept:
            serial_info["pending"] = False
            serial_info["accept"] = True
            serial_info["resolved"] = True
        return QuotaHolderSerial.objects.create(**serial_info)
    else:
        raise Exception("No serial")


def accept_serial(serial, strict=True):
    assert serial.pending or serial.accept
    response = resolve_commissions(accept=[serial.serial], strict=strict)
    serial.pending = False
    serial.accept = True
    serial.resolved = True
    serial.save()
    return response


def reject_serial(serial, strict=True):
    assert serial.pending or not serial.accept
    response = resolve_commissions(reject=[serial.serial], strict=strict)
    serial.pending = False
    serial.accept = False
    serial.resolved = True
    serial.save()
    return response


def accept_commissions(accepted, strict=True):
    return resolve_commissions(accept=accepted, strict=strict)


def reject_commissions(rejected, strict=True):
    return resolve_commissions(reject=rejected, strict=strict)


def resolve_commissions(accept=None, reject=None, strict=True):
    if accept is None:
        accept = []
    if reject is None:
        reject = []

    qh = Quotaholder.get()
    with AstakosClientExceptionHandler():
        response = qh.resolve_commissions(accept, reject)

    if strict:
        failed = response["failed"]
        if failed:
            log.error("Unexpected error while resolving commissions: %s",
                      failed)

    return response


def fix_pending_commissions():
    (accepted, rejected) = resolve_pending_commissions()
    resolve_commissions(accept=accepted, reject=rejected)


def resolve_pending_commissions():
    """Resolve quotaholder pending commissions.

    Get pending commissions from the quotaholder and resolve them
    to accepted and rejected, according to the state of the
    QuotaHolderSerial DB table. A pending commission in the quotaholder
    can exist in the QuotaHolderSerial table and be either accepted or
    rejected, or cannot exist in this table, so it is rejected.

    """

    qh_pending = get_quotaholder_pending()
    if not qh_pending:
        return ([], [])

    qh_pending.sort()
    min_ = qh_pending[0]

    serials = QuotaHolderSerial.objects.filter(serial__gte=min_, pending=False)
    accepted = serials.filter(accept=True).values_list('serial', flat=True)
    accepted = filter(lambda x: x in qh_pending, accepted)

    rejected = list(set(qh_pending) - set(accepted))

    return (accepted, rejected)


def get_quotaholder_pending():
    qh = Quotaholder.get()
    pending_serials = qh.get_pending_commissions()
    return pending_serials


def render_overlimit_exception(e):
    resource_name = {"vm": "Virtual Machine",
                     "cpu": "CPU",
                     "ram": "RAM",
                     "network.private": "Private Network",
                     "floating_ip": "Floating IP address"}
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


@transaction.commit_on_success
def issue_and_accept_commission(resource, action="BUILD", action_fields=None):
    """Issue and accept a commission to Quotaholder.

    This function implements the Commission workflow, and must be called
    exactly after and in the same transaction that created/updated the
    resource. The workflow that implements is the following:
    0) Resolve previous unresolved commission if exists
    1) Issue commission, get a serial and correlate it with the resource
    2) Store the serial in DB as a serial to accept
    3) COMMIT!
    4) Accept commission to QH

    """
    commission_reason = ("client: api, resource: %s, action: %s"
                         % (resource, action))
    serial = handle_resource_commission(resource=resource, action=action,
                                        action_fields=action_fields,
                                        commission_name=commission_reason)

    # Mark the serial as one to accept and associate it with the resource
    serial.pending = False
    serial.accept = True
    serial.save()
    transaction.commit()

    try:
        # Accept the commission to quotaholder
        accept_serial(serial)
    except:
        # Do not crash if we can not accept commission to Quotaholder. Quotas
        # have already been reserved and the resource already exists in DB.
        # Just log the error
        log.exception("Failed to accept commission: %s", serial)

    return serial


def get_commission_info(resource, action, action_fields=None):
    if isinstance(resource, VirtualMachine):
        flavor = resource.flavor
        resources = {"cyclades.vm": 1,
                     "cyclades.cpu": flavor.cpu,
                     "cyclades.disk": 1073741824 * flavor.disk,
                     "cyclades.ram": 1048576 * flavor.ram}
        online_resources = {"cyclades.active_cpu": flavor.cpu,
                            "cyclades.active_ram": 1048576 * flavor.ram}
        if action == "BUILD":
            resources.update(online_resources)
            return resources
        if action == "START":
            if resource.operstate == "STOPPED":
                return online_resources
            else:
                return None
        elif action == "STOP":
            if resource.operstate in ["STARTED", "BUILD", "ERROR"]:
                return reverse_quantities(online_resources)
            else:
                return None
        elif action == "REBOOT":
            if resource.operstate == "STOPPED":
                return online_resources
            else:
                return None
        elif action == "DESTROY":
            if resource.operstate in ["STARTED", "BUILD", "ERROR"]:
                resources.update(online_resources)
            return reverse_quantities(resources)
        elif action == "RESIZE" and action_fields:
            beparams = action_fields.get("beparams")
            cpu = beparams.get("vcpus", flavor.cpu)
            ram = beparams.get("maxmem", flavor.ram)
            return {"cyclades.cpu": cpu - flavor.cpu,
                    "cyclades.ram": 1048576 * (ram - flavor.ram)}
        else:
            #["CONNECT", "DISCONNECT", "SET_FIREWALL_PROFILE"]:
            return None
    elif isinstance(resource, Network):
        resources = {"cyclades.network.private": 1}
        if action == "BUILD":
            return resources
        elif action == "DESTROY":
            return reverse_quantities(resources)
    elif isinstance(resource, FloatingIP):
        resources = {"cyclades.floating_ip": 1}
        if action == "BUILD":
            return resources
        elif action == "DESTROY":
            return reverse_quantities(resources)


def reverse_quantities(resources):
    return dict((r, -s) for r, s in resources.items())


def handle_resource_commission(resource, action, commission_name,
                               force=False, auto_accept=False,
                               action_fields=None):
    """Handle a issuing of a commission for a resource.

    Create a new commission for a resource based on the action that
    is performed. If the resource has a previous pending commission,
    resolved it before issuing the new one.

    """
    # Try to resolve previous serial
    resolve_commission(resource.serial, force=force)

    serial = issue_commission(resource, action, name=commission_name,
                              force=force, auto_accept=auto_accept,
                              action_fields=action_fields)
    resource.serial = serial
    resource.save()
    return serial


class ResolveError(Exception):
    pass


def resolve_commission(serial, force=False):
    if serial is None or serial.resolved:
        return
    if serial.pending and not force:
        m = "Could not resolve commission: serial %s is undecided" % serial
        raise ResolveError(m)
    log.warning("Resolving pending commission: %s", serial)
    if not serial.pending and serial.accept:
        accept_serial(serial)
    else:
        reject_serial(serial)
