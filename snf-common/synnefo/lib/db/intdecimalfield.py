from django.core import exceptions
from django.db.models import DecimalField, SubfieldBase
from django.utils.translation import ugettext_lazy as _
import decimal

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
        return connection.ops.value_to_db_decimal(self._to_decimal(value),
                self.max_digits, self.decimal_places)

    def get_prep_value(self, value):
        return self._to_decimal(value)

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.IntegerField}
        defaults.update(kwargs)
        return super(IntegerField, self).formfield(**defaults)

from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^synnefo\.lib\.db\.intdecimalfield\.IntDecimalField"])

DECIMAL_DIGITS  =   38

def intDecimalField(verbose_name=None, name=None, **kwargs):
    # decimal_places is set here instead of the object constructor
    # in order to convince south
    return IntDecimalField(verbose_name, name, max_digits=DECIMAL_DIGITS, decimal_places=0, **kwargs)
