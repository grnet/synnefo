# Copyright (C) 2010-2017 GRNET S.A.
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


def build_version_object(url, version_id, path, status, **extra_args):
    """Generates a version object

    The version object is structured based on the OpenStack
    API. `extra_args` is for supporting extra information about
    the version such as media types, extra links etc
    """
    base_version = {
        'id': 'v%s' % version_id,
        'status': status,
        'links': [
            {
                'rel': 'self',
                'href': '%s/%s/' % (url, path),
            },
        ],
    }
    return dict(base_version, **extra_args)
