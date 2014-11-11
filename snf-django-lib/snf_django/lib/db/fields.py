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

from django.core import exceptions
from django.db.models import DecimalField, SubfieldBase
from django import forms
from django.utils.translation import ugettext_lazy as _
from south.modelsinspector import add_introspection_rules
import decimal

DECIMAL_DIGITS = 38


class IntDecimalField(DecimalField):

    __metaclass__ = SubfieldBase

    description = _("Integer number as decimal")

    def to_python(self, value):
        if value is None:
            return value
        try:
            return long(value)
        except (ValueError, TypeError):
            raise exceptions.ValidationError(self.error_messages['invalid'])

    def _to_decimal(self, value):
        if value is None:
            return value
        try:
            return decimal.Decimal(value)
        except decimal.InvalidOperation:
            raise exceptions.ValidationError(self.error_messages['invalid'])

    def get_db_prep_save(self, value, connection):
        return connection.ops.value_to_db_decimal(
            self._to_decimal(value), self.max_digits, self.decimal_places)

    def get_prep_value(self, value):
        return self._to_decimal(value)

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.IntegerField}
        defaults.update(kwargs)
        return super(IntDecimalField, self).formfield(**defaults)

add_introspection_rules(
    [], ["^snf_django\.lib\.db\.fields\.IntDecimalField"])


def intDecimalField(verbose_name=None, name=None, **kwargs):
    # decimal_places is set here instead of the object constructor
    # in order to convince south
    return IntDecimalField(verbose_name, name,
                           max_digits=DECIMAL_DIGITS, decimal_places=0,
                           **kwargs)
