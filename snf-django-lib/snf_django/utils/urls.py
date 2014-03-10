# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

from django.conf.urls import url, patterns

from snf_django.lib.api.utils import prefix_pattern
from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls


def extend_path_with_slash(patterns_obj, path):
    if not path.endswith('/'):
        pattern = prefix_pattern(path, append_slash=False) + '$'
        entry = url(pattern, 'redirect_to', {'url': path + '/'})
        patterns_obj += patterns('django.views.generic.simple', entry)


def extend_endpoint_with_slash(patterns_obj, filled_services, service_type,
                               version=None):
    path = get_service_path(filled_services, service_type, version)
    extend_path_with_slash(patterns_obj, path)


def extend_with_root_redirects(patterns_obj, filled_services, service_type,
                               base_path, with_slash=True):
    """
    Append additional redirect url entries for `/` and `/<base_path>` paths.

    `/` redirects to `/<base_path>` and `/<base_path>` to the resolved service
    type url.

    This is used in synnefo components root urlpatterns to append sane default
    redirects to the chosen service url.

    """
    service_path = get_service_path(filled_services, service_type)
    if with_slash:
        service_path = service_path.rstrip('/') + '/'

    root_url_entry = None
    if base_path and base_path != '/':
        # redirect slash to /<base_path>/
        root_url_entry = url('^$', 'redirect_to',
                             {'url': join_urls('/', base_path.rstrip('/'),
                                               '/')})

    base_path_pattern = prefix_pattern(base_path) + '$'
    base_path_pattern_no_slash = prefix_pattern(base_path).rstrip('/') + '$'

    # redirect /<base_path> and /<base_path>/ to service_path public endpoint
    base_url_entry = url(base_path_pattern, 'redirect_to', {'url':
                                                            service_path})
    base_url_entry_no_slash = url(base_path_pattern_no_slash,
                                  'redirect_to', {'url': service_path})
    # urls order matter. Setting base_url_entry first allows us to avoid
    # redirect loops when base_path is empty or `/`
    patterns_obj += patterns('django.views.generic.simple',
                             base_url_entry, base_url_entry_no_slash)
    if root_url_entry:
        # register root entry only for non root base_path deployments
        patterns_obj += patterns('django.views.generic.simple', root_url_entry)
