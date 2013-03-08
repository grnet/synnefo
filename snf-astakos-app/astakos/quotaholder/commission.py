# Copyright 2013 GRNET S.A. All rights reserved.
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

from astakos.quotaholder.exception import (
    NoCapacityError, NoStockError,
    NonImportedError, NoStockReleaseError, NonExportedError)


class Operation(object):

    @staticmethod
    def assertions(holding):
        assert(0 <= holding.imported_min)
        assert(holding.imported_min <= holding.imported_max)
        assert(0 <= holding.stock_min)
        assert(holding.stock_min <= holding.stock_max)

    @classmethod
    def _prepare(cls, holding, quantity, check=True):
        raise NotImplementedError

    @classmethod
    def prepare(cls, holding, quantity, check=True):
        cls.assertions(holding)
        cls._prepare(holding, quantity, check=True)

    @classmethod
    def _finalize(cls, holding, quantity):
        raise NotImplementedError

    @classmethod
    def finalize(cls, holding, quantity):
        cls.assertions(holding)
        cls._finalize(holding, quantity)

    @classmethod
    def undo(cls, holding, quantity):
        cls.prepare(holding, -quantity, check=False)

    @classmethod
    def revert(cls, holding, quantity):
        # Assertions do not hold when reverting
        cls._prepare(holding, -quantity, check=False)


class Import(Operation):

    @classmethod
    def _prepare(cls, holding, quantity, check=True):
        imported_max = holding.imported_max
        new_imported_max = imported_max + quantity

        capacity = holding.capacity
        if check and new_imported_max > capacity:
            holder = holding.holder
            resource = holding.resource
            m = ("%s has not enough capacity of %s." % (holder, resource))
            raise NoCapacityError(m,
                                  holder=holder,
                                  resource=resource,
                                  requested=quantity,
                                  current=imported_max,
                                  limit=capacity)

        holding.imported_max = new_imported_max
        holding.save()

    @classmethod
    def _finalize(cls, holding, quantity):
        holding.imported_min += quantity
        holding.stock_min += quantity
        holding.stock_max += quantity
        holding.save()


class Export(Operation):

    @classmethod
    def _prepare(cls, holding, quantity, check=True):
        stock_min = holding.stock_min
        new_stock_min = stock_min - quantity

        if check and new_stock_min < 0:
            holder = holding.holder
            resource = holding.resource
            m = ("%s has not enough stock of %s." % (holder, resource))
            raise NoStockError(m,
                               holder=holder,
                               resource=resource,
                               requested=quantity,
                               limit=stock_min)

        holding.stock_min = new_stock_min
        holding.save()

    @classmethod
    def _finalize(cls, holding, quantity):
        holding.stock_max -= quantity
        holding.save()


class Release(Operation):

    @classmethod
    def _prepare(cls, holding, quantity, check=True):
        imported_min = holding.imported_min
        new_imported_min = imported_min - quantity

        stock_min = holding.stock_min
        new_stock_min = stock_min - quantity
        stock_max = holding.stock_max
        new_stock_max = stock_max - quantity

        if check and new_imported_min < 0:
            holder = holding.holder
            resource = holding.resource
            m = ("%s attempts to release more %s than it contains." %
                 (holder, resource))
            raise NonImportedError(m,
                                   holder=holder,
                                   resource=resource,
                                   requested=quantity,
                                   limit=imported_min)

        if check and new_stock_min < 0:
            holder = holding.holder
            resource = holding.resource
            m = ("%s attempts to release %s that has been reexported." %
                 (holder, resource))
            raise NoStockReleaseError(m,
                                      holder=holder,
                                      resource=resource,
                                      requested=quantity,
                                      limit=stock_min)

        holding.imported_min = new_imported_min
        holding.stock_min = new_stock_min
        holding.stock_max = new_stock_max
        holding.save()

    @classmethod
    def _finalize(cls, holding, quantity):
        holding.imported_max -= quantity
        holding.save()


class Reclaim(Operation):

    @classmethod
    def _prepare(cls, holding, quantity, check=True):
        stock_max = holding.stock_max
        new_stock_max = stock_max + quantity

        imported_min = holding.imported_min
        if check and new_stock_max > imported_min:
            holder = holding.holder
            resource = holding.resource
            m = ("%s attempts to reclaim %s not originating by itself." %
                 (holder, resource))
            raise NonExportedError(m,
                                   holder=holder,
                                   resource=resource,
                                   requested=quantity,
                                   current=stock_max,
                                   limit=imported_min)

        holding.stock_max = new_stock_max
        holding.save()

    @classmethod
    def _finalize(cls, holding, quantity):
        holding.stock_min += quantity
        holding.save()


class Operations(object):
    def __init__(self):
        self.operations = []

    def prepare(self, operation, holding, quantity):
        operation.prepare(holding, quantity)
        self.operations.append((operation, holding, quantity))

    def finalize(self, operation, holding, quantity):
        operation.finalize(holding, quantity)
        self.operations.append((operation, holding, quantity))

    def undo(self, operation, holding, quantity):
        operation.undo(holding, quantity)
        self.operations.append((operation, holding, quantity))

    def revert(self):
        for (operation, holding, quantity) in self.operations:
            operation.revert(holding, quantity)
