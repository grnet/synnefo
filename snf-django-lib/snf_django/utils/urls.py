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
