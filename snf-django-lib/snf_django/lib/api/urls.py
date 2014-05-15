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

from django.core import urlresolvers
from django.views.decorators import csrf
from django.conf.urls import patterns


def _patch_pattern(regex_pattern):
    """
    Patch pattern callback using csrf_exempt. Enforce
    RegexURLPattern callback to get resolved if required.

    """
    regex_pattern._callback = \
        csrf.csrf_exempt(regex_pattern.callback)


def _patch_resolver(r):
    """
    Patch all patterns found in resolver with _patch_pattern
    """
    if hasattr(r, 'url_patterns'):
        entries = r.url_patterns
    else:
        # first level view in patterns ?
        entries = [r]

    for entry in entries:
        if isinstance(entry, urlresolvers.RegexURLResolver):
            _patch_resolver(entry)
        #if isinstance(entry, urlresolvers.RegexURLPattern):
        # let it break...
        else:
            _patch_pattern(entry)


def api_patterns(*args, **kwargs):
    """
    Protect all url patterns from csrf attacks.
    """
    _patterns = patterns(*args, **kwargs)
    for entry in _patterns:
        _patch_resolver(entry)
    return _patterns
