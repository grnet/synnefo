# Copyright 2012, 2013 GRNET S.A. All rights reserved.
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

from django.core import urlresolvers
from django.views.decorators import csrf
try:
    from django.conf.urls import patterns
except ImportError:  # Django==1.2
    from django.conf.urls.defaults import patterns



def _patch_pattern(regex_pattern):
    """
    Patch pattern callback using csrf_exempt. Enforce
    RegexURLPattern callback to get resolved if required.

    """
    if hasattr(regex_pattern, "_get_callback"):  # Django==1.2
        if not regex_pattern._callback:
            # enforce _callback resolving
            regex_pattern._get_callback()

        regex_pattern._callback = \
            csrf.csrf_exempt(regex_pattern._callback)
    else:
        regex_pattern._callback = \
            csrf.csrf_exempt(regex_pattern.callback)


def _patch_resolver(r):
    """
    Patch all patterns found in resolver with _patch_pattern
    """
    if hasattr(r, '_get_url_patterns'):  # Django ==1.2
        entries = r._get_url_patterns()
    elif hasattr(r, 'url_patterns'):
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
