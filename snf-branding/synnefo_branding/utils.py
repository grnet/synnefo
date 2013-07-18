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
