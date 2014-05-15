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

from astakos.quotaholder_app.exception import NoCapacityError, NoQuantityError


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
                                  limit=0,
                                  usage=usage_min)

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
