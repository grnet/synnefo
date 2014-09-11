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
from snf_django.utils.urls import extend_path_with_slash
from snf_django.lib.api.utils import prefix_pattern
from synnefo_admin.admin_settings import BASE_PATH

urlpatterns = patterns(
    '',
    (prefix_pattern(BASE_PATH), include('synnefo_admin.admin.urls')),
)

extend_path_with_slash(urlpatterns, BASE_PATH)
