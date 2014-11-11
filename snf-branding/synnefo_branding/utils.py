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

from django.conf import settings as django_settings
from synnefo_branding import settings
from django.template.loader import render_to_string as django_render_to_string


def get_branding_dict(prepend=None):
    # CONTACT_EMAIL may not be a branding setting. We include it here though
    # for practial reasons.
    dct = {'support': django_settings.CONTACT_EMAIL}
    for key in dir(settings):
        if key == key.upper():
            newkey = key.lower()
            if prepend:
                newkey = '%s_%s' % (prepend, newkey)
            dct[newkey.upper()] = getattr(settings, key)
    return dct


def brand_message(msg, **extra_args):
    params = get_branding_dict()
    params.update(extra_args)
    return msg % params


def render_to_string(template_name, dictionary=None, context_instance=None):
    if not dictionary:
        dictionary = {}

    if isinstance(dictionary, dict):
        newdict = get_branding_dict("BRANDING")
        newdict.update(dictionary)
    else:
        newdict = dictionary

    return django_render_to_string(template_name, newdict, context_instance)
