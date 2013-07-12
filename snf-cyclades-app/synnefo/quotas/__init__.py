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
from synnefo.db.models import QuotaHolderSerial, VirtualMachine, Network

from synnefo.settings import (CYCLADES_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_BASE_URL)
from astakosclient import AstakosClient
from astakosclient.errors import AstakosClientException, QuotaLimit
from functools import wraps

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
                ASTAKOS_BASE_URL,
                use_pool=True,
                retry=3,
                logger=log)
        return cls._object


def handle_astakosclient_error(func):
    """Decorator for converting astakosclient errors to 500."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AstakosClientException:
            log.exception("Unexpected error")
            raise faults.InternalServerError("Unexpected error")
    return wrapper


@handle_astakosclient_error
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
                                         force=force, auto_accept=auto_accept)
    except QuotaLimit as e:
        msg, details = render_overlimit_exception(e)
        raise faults.OverLimit(msg, details=details)

    if serial:
        return QuotaHolderSerial.objects.create(serial=serial)
    else:
        raise Exception("No serial")


def accept_commissions(accepted, strict=True):
    return resolve_commissions(accept=accepted, strict=strict)


def reject_commissions(rejected, strict=True):
    return resolve_commissions(reject=rejected, strict=strict)


@handle_astakosclient_error
def resolve_commissions(accept=None, reject=None, strict=True):
    if accept is None:
        accept = []
    if reject is None:
        reject = []

    qh = Quotaholder.get()
    response = qh.resolve_commissions(ASTAKOS_TOKEN, accept, reject)

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
    rejected, or can not exist in this table, so it is rejected.

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


@transaction.commit_manually
def issue_and_accept_commission(resource, delete=False):
    """Issue and accept a commission to Quotaholder.

    This function implements the Commission workflow, and must be called
    exactly after and in the same transaction that created/updated the
    resource. The workflow that implements is the following:
    0) Resolve previous unresolved commission if exists
    1) Issue commission and get a serial
    2) Store the serial in DB and mark is as one to accept
    3) Correlate the serial with the resource
    4) COMMIT!
    5) Accept commission to QH (reject if failed until 5)
    6) Mark serial as resolved
    7) COMMIT!

    """
    previous_serial = resource.serial
    if previous_serial is not None and not previous_serial.resolved:
        if previous_serial.pending:
            msg = "Issuing commission for resource '%s' while previous serial"\
                  " '%s' is still pending." % (resource, previous_serial)
            raise Exception(msg)
        elif previous_serial.accept:
            accept_commissions(accepted=[previous_serial.serial], strict=False)
        else:
            reject_commissions(rejected=[previous_serial.serial], strict=False)
        previous_serial.resolved = True

    try:
        # Convert resources in the format expected by Quotaholder
        qh_resources = prepare_qh_resources(resource)
        if delete:
            qh_resources = reverse_quantities(qh_resources)

        # Issue commission and get the assigned serial
        serial = issue_commission(resource.userid, DEFAULT_SOURCE,
                                  qh_resources)
    except:
        transaction.rollback()
        raise

    try:
        # Mark the serial as one to accept. This step is necessary for
        # reconciliation
        serial.pending = False
        serial.accept = True
        serial.save()

        # Associate serial with the resource
        resource.serial = serial
        resource.save()

        # Commit transaction in the DB! If this commit succeeds, then the
        # serial is created in the DB with all the necessary information to
        # reconcile commission
        transaction.commit()
    except:
        transaction.rollback()
        serial.pending = False
        serial.accept = False
        serial.save()
        transaction.commit()
        raise

    if serial.accept:
        # Accept commission to Quotaholder
        accept_commissions(accepted=[serial.serial])
    else:
        reject_commissions(rejected=[serial.serial])

    # Mark the serial as resolved, indicating that no further actions are
    # needed for this serial
    serial.resolved = True
    serial.save()
    transaction.commit()

    return serial


def prepare_qh_resources(resource):
    if isinstance(resource, VirtualMachine):
        flavor = resource.flavor
        return {'cyclades.vm': 1,
                'cyclades.cpu': flavor.cpu,
                'cyclades.disk': 1073741824 * flavor.disk,  # flavor.disk in GB
                # 'public_ip': 1,
                #'disk_template': flavor.disk_template,
                'cyclades.ram': 1048576 * flavor.ram}  # flavor.ram is in MB
    elif isinstance(resource, Network):
        return {"cyclades.network.private": 1}
    else:
        raise ValueError("Unknown Resource '%s'" % resource)


def reverse_quantities(resources):
    return dict((r, -s) for r, s in resources.items())
