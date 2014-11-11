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

from django.db import models
from south.modelsinspector import add_introspection_rules


class SeparatedValuesField(models.TextField):
    description = ("Stores list of values as a TextField,"
                   " separated by a delimiter.")
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        self.delimiter = kwargs.pop('delimiter', ',')
        super(SeparatedValuesField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if not value:
            return []
        if isinstance(value, list):
            return value
        return value.split(self.delimiter)

    def get_prep_value(self, value):
        if not value:
            return
        assert(isinstance(value, list) or isinstance(value, tuple))
        return self.delimiter.join([unicode(s) for s in value])

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)


add_introspection_rules([
    (
        [SeparatedValuesField],  # Class(es) these apply to
        [],         # Positional arguments (not used)
        {           # Keyword argument
            "delimiter": ["delimiter", {"default": ","}],
        },
    ),
], ["^synnefo\.db\.fields\.SeparatedValuesField"])
