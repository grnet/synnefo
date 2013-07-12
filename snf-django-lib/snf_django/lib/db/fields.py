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
