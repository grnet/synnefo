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
from django.conf.urls import patterns, url

from django.conf import settings

urlpatterns = patterns(
    '',
    url(r'^$', 'synnefo.ui.views.home', name='ui_index'),
    url(r'^machines/console$', 'synnefo.ui.views.machines_console',
        name='ui_machines_console'),
    url(r'^machines/connect$', 'synnefo.ui.views.machines_connect',
        name='ui_machines_connect'),
)

if settings.DEBUG or settings.TEST:
    urlpatterns += patterns(
        '', url(r'^jstests$', 'synnefo.ui.views.js_tests', name='js_tests'),)
