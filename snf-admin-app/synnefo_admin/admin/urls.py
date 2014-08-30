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
#

"""Url configuration for the admin interface"""

from django.conf.urls import patterns, url

urlpatterns = patterns(
    'synnefo_admin.admin.views',
    url(r'^$', 'catalog', name='admin-default'),
    url(r'^home$', 'home', name='admin-home'),
    url(r'^logout$', 'logout', name='admin-logout'),
    url(r'^charts$', 'charts', name='admin-charts'),
    url(r'^stats$', 'stats', name='admin-stats'),
    url(r'^stats/(?P<component>.*)/detail$', 'stats_component_details',
        name='admin-stats-component-details'),
    url(r'^stats/(?P<component>.*)$', 'stats_component',
        name='admin-stats-component'),
    url(r'^json/(?P<type>.*)$', 'json_list', name='admin-json'),
    url(r'^actions/$', 'admin_actions', name='admin-actions'),
    url(r'^(?P<type>.*)/(?P<id>.*)$', 'details', name='admin-details'),
    url(r'^(?P<type>.*)$', 'catalog', name='admin-list'),
)
