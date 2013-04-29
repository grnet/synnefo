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

from astakos.quotaholder.exception import NoCapacityError, NoQuantityError


class Operation(object):

    @staticmethod
    def assertions(holding):
        assert(holding.usage_min <= holding.usage_max)

    @classmethod
    def _prepare(cls, holding, quantity, check=True):
        raise NotImplementedError

    @classmethod
    def prepare(cls, holding, quantity, check=True):
        cls.assertions(holding)
        cls._prepare(holding, quantity, check)

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

    @classmethod
    def provision(cls, holding, quantity, importing=True):
        return {'holder': holding.holder,
                'source': holding.source,
                'resource': holding.resource,
                'quantity': quantity if importing else -quantity,
                }


class Import(Operation):

    @classmethod
    def _prepare(cls, holding, quantity, check=True):
        usage_max = holding.usage_max
        new_usage_max = usage_max + quantity

        limit = holding.limit
        if check and new_usage_max > limit:
            holder = holding.holder
            resource = holding.resource
            m = ("%s has not enough capacity of %s." % (holder, resource))
            provision = cls.provision(holding, quantity, importing=True)
            raise NoCapacityError(m,
                                  provision=provision,
                                  limit=limit,
                                  usage=usage_max)

        holding.usage_max = new_usage_max
        holding.save()

    @classmethod
    def _finalize(cls, holding, quantity):
        holding.usage_min += quantity
        holding.save()


class Release(Operation):

    @classmethod
    def _prepare(cls, holding, quantity, check=True):
        usage_min = holding.usage_min
        new_usage_min = usage_min - quantity

        if check and new_usage_min < 0:
            holder = holding.holder
            resource = holding.resource
            m = ("%s attempts to release more %s than it contains." %
                 (holder, resource))
            provision = cls.provision(holding, quantity, importing=False)
            raise NoQuantityError(m,
                                  provision=provision,
                                  available=usage_min)

        holding.usage_min = new_usage_min
        holding.save()

    @classmethod
    def _finalize(cls, holding, quantity):
        holding.usage_max -= quantity
        holding.save()


class Operations(object):
    def __init__(self):
        self.operations = []

    def prepare(self, operation, holding, quantity, force):
        check = not force
        operation.prepare(holding, quantity, check)
        self.operations.append((operation, holding, quantity))

    def revert(self):
        for (operation, holding, quantity) in self.operations:
            operation.revert(holding, quantity)


def finalize(operation, holding, quantity):
    operation.finalize(holding, quantity)


def undo(operation, holding, quantity):
    operation.undo(holding, quantity)
