# Copyright (C) 2010-2016 GRNET S.A.
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

from __future__ import division


class FilterBase(object):

    def filter_backends(self, backends, vm):
        """
        Filter backends based on the requested VM attributes.

        The `filter_backends` method takes 2 arguments:
        1. A list of the backends to consider for VM allocation.  Each backend
        is a django object and is an instance of the `Backend` model.
        2. A VM dictionary containing attributes regarding the VM. For the
        precise list of keys refer to the backend_allocator code.

        The `Backend` model instances are not locked in the database
        so changing their attributes is not advised. The `filter_backends`
        method should treat the instances as "Read Only".
        """
        raise NotImplementedError(
            'The implementation of `filter_backends` is required.'
        )
