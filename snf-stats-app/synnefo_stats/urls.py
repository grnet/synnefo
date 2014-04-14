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

from django.conf.urls import patterns, include

from snf_django.lib.api.utils import prefix_pattern
from snf_django.lib.api import api_endpoint_not_found

from synnefo_stats.stats_settings import BASE_PATH
from synnefo_stats.grapher import grapher

graph_types_re = '((cpu|net)-(bar|(ts(-w)?)))'
stats_v1_patterns = patterns(
    '',
    (r'^(?P<graph_type>%s)/(?P<hostname>[^ /]+)$' % graph_types_re, grapher),
)

stats_patterns = patterns(
    '',
    (r'^v1.0/', include(stats_v1_patterns)),
    (r'^.*', api_endpoint_not_found),
)

urlpatterns = patterns(
    '',
    (prefix_pattern(BASE_PATH), include(stats_patterns)),
)
