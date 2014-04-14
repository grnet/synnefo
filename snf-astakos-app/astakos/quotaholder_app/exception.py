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


class QuotaholderError(Exception):
    pass


class NoCommissionError(QuotaholderError):
    pass


class CorruptedError(QuotaholderError):
    pass


class InvalidDataError(QuotaholderError):
    pass


class CommissionException(QuotaholderError):
    data = {}

    def add_data(self, kwargs, key):
        value = kwargs.pop(key, None)
        if value is not None:
            self.data[key] = value

    def __init__(self, *args, **kwargs):
        self.data['name'] = self.__class__.__name__
        self.add_data(kwargs, 'provision')

        QuotaholderError.__init__(self, *args, **kwargs)


class OverLimitError(CommissionException):
    def __init__(self, *args, **kwargs):
        self.add_data(kwargs, 'usage')
        self.add_data(kwargs, 'limit')
        CommissionException.__init__(self, *args, **kwargs)


class NoCapacityError(OverLimitError):
    pass


class NoQuantityError(OverLimitError):
    pass


class NoHoldingError(CommissionException):
    pass
