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

import re

from django.utils.translation import ugettext as _
from django.utils.encoding import smart_str
from django.utils.encoding import force_unicode as force_text
from django.utils.safestring import mark_safe
from django import forms
from django.forms import widgets
from django.core import validators

from synnefo.util import units


class EmailValidator(object):
    """
    Email validator. Backported from django 1.6
    """
    message = _('Enter a valid email address.')
    code = 'invalid'
    user_regex = re.compile(
        r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*$"  # dot-atom
        r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-\011\013\014\016-\177])*"$)', # quoted-string
        re.IGNORECASE)
    domain_regex = re.compile(
        r'(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}|[A-Z0-9-]{2,})$'  # domain
        # literal form, ipv4 address (SMTP 4.1.3)
        r'|^\[(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}\]$',
        re.IGNORECASE)
    domain_whitelist = ['localhost']

    def __init__(self, message=None, code=None, whitelist=None):
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        if whitelist is not None:
            self.domain_whitelist = whitelist

    def __call__(self, value):
        value = force_text(value)

        if not value or '@' not in value:
            raise forms.ValidationError(self.message, code=self.code)

        user_part, domain_part = value.rsplit('@', 1)

        if not self.user_regex.match(user_part):
            raise forms.ValidationError(self.message, code=self.code)

        if (not domain_part in self.domain_whitelist and
                not self.domain_regex.match(domain_part)):
            # Try for possible IDN domain-part
            try:
                domain_part = domain_part.encode('idna').decode('ascii')
                if not self.domain_regex.match(domain_part):
                    raise forms.ValidationError(self.message, code=self.code)
                else:
                    return
            except UnicodeError:
                pass
            raise forms.ValidationError(self.message, code=self.code)


class EmailField(forms.EmailField):
    default_validators = [EmailValidator()]


class CustomChoiceWidget(forms.MultiWidget):

    def __init__(self, attrs=None, **kwargs):
        _widgets = (
            widgets.Select(attrs=attrs, **kwargs),
            widgets.TextInput(attrs=attrs)
        )
        super(CustomChoiceWidget, self).__init__(_widgets, attrs)

    def render(self, *args, **kwargs):
        attrs = kwargs.get("attrs", {})
        css_class = attrs.get("class", "") + " custom-select"
        attrs['class'] = css_class
        kwargs['attrs'] = attrs
        out = super(CustomChoiceWidget, self).render(*args, **kwargs)
        return mark_safe("""
%(html)s
<script>
$(document).ready(function() {
    var select = $("#%(id)s_0");
    var input = $("#%(id)s_1");
    input.hide();
    var check_custom = function() {
        var val = select.val();
        if (val == "custom") {
            input.show().focus();
        } else {
            input.hide().val('');
        }
    }
    select.bind("change", check_custom);
    check_custom();
});
</script>
""" % ({
    'id': attrs.get("id"),
    'html': out
}))

    def decompress(self, value):
        if not value:
            return ['custom', '']
        if value == 'Unlimited':
            return ['Unlimited', '']

        try:
            value = int(value)
        except ValueError:
            return ['custom', value]

        values = dict(self.choices).values()

        if value in values:
            return [str(value), '']
        else:
            return ['custom', str(value)]

    def value_from_datadict(self, *args, **kwargs):
        value = super(CustomChoiceWidget, self).value_from_datadict(*args,
                                                                    **kwargs)
        if value[0] == "custom":
            return value[1]
        return value[0]


class InfiniteChoiceField(forms.ChoiceField):
    """
    A custom integer choice field which allows user to set a custom value.
    """

    INFINITE_VALUES = ['Unlimited']
    widget = CustomChoiceWidget
    default_validators=[validators.MinValueValidator(0)]

    def _get_choices(self):
        return self._choices

    def _set_choices(self, value):
        self._choices = self.widget.choices = \
            self.widget.widgets[0].choices = \
                list(value) + [("custom", "Other")]

    choices = property(_get_choices, _set_choices)

    def to_python(self, value):
        """
        Handle infinite values.
        """
        if value in self.INFINITE_VALUES:
            value = units.PRACTICALLY_INFINITE
        value = super(InfiniteChoiceField, self).to_python(value)
        try:
            value = int(str(value))
        except (ValueError, TypeError):
            raise forms.ValidationError(self.error_messages['invalid'])
        return value

    def validate(self, value):
        try:
            value = int(str(value))
        except (ValueError, TypeError):
            raise forms.ValidationError(self.error_messages['invalid'])
