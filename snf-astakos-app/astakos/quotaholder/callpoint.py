# Copyright 2012, 2013 GRNET S.A. All rights reserved.
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

from functools import partial

from astakos.quotaholder.exception import (
    QuotaholderError,
    NoCommissionError,
    CorruptedError, InvalidDataError,
    NoHoldingError,
    DuplicateError)

from astakos.quotaholder.commission import (
    Import, Release, Operations)

from astakos.quotaholder.utils.newname import newname
from astakos.quotaholder.api import QH_PRACTICALLY_INFINITE

from .models import (Holding,
                     Commission, Provision, ProvisionLog,
                     now,
                     db_get_holding,
                     db_get_commission, db_filter_provision)


class QuotaholderDjangoDBCallpoint(object):

    def get_holder_quota(self, holders=None, sources=None, resources=None):
        holdings = Holding.objects.filter(holder__in=holders)

        if sources is not None:
            holdings = holdings.filter(source__in=sources)

        if resources is not None:
            holdings = holdings.filter(resource__in=resources)

        quotas = {}
        for holding in holdings:
            key = (holding.holder, holding.source, holding.resource)
            value = (holding.limit, holding.imported_min, holding.imported_max)
            quotas[key] = value

        return quotas

    def set_holder_quota(self, quotas):
        holders = quotas.keys()
        hs = Holding.objects.filter(holder__in=holders).select_for_update()
        holdings = {}
        for h in hs:
            holdings[(h.holder, h.source, h.resource)] = h

        for holder, holder_quota in quotas.iteritems():
            for source, source_quota in holder_quota.iteritems():
                for resource, limit in source_quota.iteritems():
                    try:
                        h = holdings[(holder, source, resource)]
                    except KeyError:
                        h = Holding(holder=holder,
                                    source=source,
                                    resource=resource)

                    h.limit = limit
                    h.save()

    def issue_commission(self,
                         context=None,
                         clientkey=None,
                         name=None,
                         force=False,
                         provisions=()):

        if name is None:
            name = ""
        create = Commission.objects.create
        commission = create(clientkey=clientkey, name=name)
        serial = commission.serial

        operations = Operations()

        try:
            checked = []
            for provision in provisions:
                try:
                    holder = provision['holder']
                    source = provision['source']
                    resource = provision['resource']
                    quantity = provision['quantity']
                except KeyError:
                    raise InvalidDataError("Malformed provision")

                if not isinstance(quantity, (int, long)):
                    raise InvalidDataError("Malformed provision")

                ent_res = holder, resource
                if ent_res in checked:
                    m = "Duplicate provision for %s.%s" % ent_res
                    details = {'message': m,
                               }
                    raise DuplicateError(m,
                                         provision=provision,
                                         details=details)
                checked.append(ent_res)

                # Target
                try:
                    th = db_get_holding(holder=holder,
                                        resource=resource,
                                        source=source,
                                        for_update=True)
                except Holding.DoesNotExist:
                    m = ("There is no such holding %s.%s"
                         % (holder, resource))
                    raise NoHoldingError(m,
                                         provision=provision)

                if quantity >= 0:
                    operations.prepare(Import, th, quantity, force)

                else: # release
                    abs_quantity = -quantity
                    operations.prepare(Release, th, abs_quantity, force)

                Provision.objects.create(serial=commission,
                                         holding=th,
                                         quantity=quantity)

        except QuotaholderError:
            operations.revert()
            raise

        return serial

    def _log_provision(self,
                       commission, provision, log_time, reason):

        holding = provision.holding

        kwargs = {
            'serial':              commission.serial,
            'name':                commission.name,
            'holder':              holding.holder,
            'source':              holding.source,
            'resource':            holding.resource,
            'limit':               holding.limit,
            'imported_min':        holding.imported_min,
            'imported_max':        holding.imported_max,
            'delta_quantity':      provision.quantity,
            'issue_time':          commission.issue_time,
            'log_time':            log_time,
            'reason':              reason,
        }

        ProvisionLog.objects.create(**kwargs)

    def accept_commission(self,
                          context=None, clientkey=None,
                          serial=None, reason=''):
        log_time = now()

        try:
            c = db_get_commission(clientkey=clientkey, serial=serial,
                                  for_update=True)
        except Commission.DoesNotExist:
            return False

        operations = Operations()

        provisions = db_filter_provision(serial=serial, for_update=True)
        for pv in provisions:
            try:
                th = db_get_holding(id=pv.holding_id,
                                    for_update=True)
            except Holding.DoesNotExist:
                m = "Corrupted provision"
                raise CorruptedError(m)

            quantity = pv.quantity

            if quantity >= 0:
                operations.finalize(Import, th, quantity)
            else: # release
                abs_quantity = -quantity
                operations.finalize(Release, th, abs_quantity)

            reason = 'ACCEPT:' + reason[-121:]
            self._log_provision(c, pv, log_time, reason)
            pv.delete()
        c.delete()
        return True

    def reject_commission(self,
                          context=None, clientkey=None,
                          serial=None, reason=''):
        log_time = now()

        try:
            c = db_get_commission(clientkey=clientkey, serial=serial,
                                  for_update=True)
        except Commission.DoesNotExist:
            return False

        operations = Operations()

        provisions = db_filter_provision(serial=serial, for_update=True)
        for pv in provisions:
            try:
                th = db_get_holding(id=pv.holding_id,
                                    for_update=True)
            except Holding.DoesNotExist:
                m = "Corrupted provision"
                raise CorruptedError(m)

            quantity = pv.quantity

            if quantity >= 0:
                operations.undo(Import, th, quantity)
            else: # release
                abs_quantity = -quantity
                operations.undo(Release, th, abs_quantity)

            reason = 'REJECT:' + reason[-121:]
            self._log_provision(c, pv, log_time, reason)
            pv.delete()
        c.delete()
        return True

    def get_pending_commissions(self, context=None, clientkey=None):
        pending = Commission.objects.filter(clientkey=clientkey)
        pending_list = pending.values_list('serial', flat=True)
        return list(pending_list)

    def get_commission(self, clientkey=None, serial=None):
        try:
            commission = Commission.objects.get(clientkey=clientkey,
                                                serial=serial)
        except Commission.DoesNotExist:
            raise NoCommissionError(serial)

        objs = Provision.objects.select_related('holding')
        provisions = objs.filter(serial=commission)

        ps = [p.todict() for p in provisions]

        response = {'serial':     serial,
                    'provisions': ps,
                    'issue_time': commission.issue_time,
                    }
        return response

    def _resolve(self, include, exclude, operation):
        done = []
        failed = []
        for serial in include:
            if serial in exclude:
                failed.append((serial, 'CONFLICT'))
            else:
                response = operation(serial=serial)
                if response:
                    done.append(serial)
                else:
                    failed.append((serial, 'NOTFOUND'))
        return done, failed

    def resolve_pending_commissions(self,
                                    context=None, clientkey=None,
                                    accept_set=[], reject_set=[]):
        accept_set = set(accept_set)
        reject_set = set(reject_set)

        accept = partial(self.accept_commission, clientkey=clientkey)
        reject = partial(self.reject_commission, clientkey=clientkey)

        accepted, failed_ac = self._resolve(accept_set, reject_set, accept)
        rejected, failed_re = self._resolve(reject_set, accept_set, reject)

        failed = list(set(failed_ac + failed_re))
        return accepted, rejected, failed


API_Callpoint = QuotaholderDjangoDBCallpoint
