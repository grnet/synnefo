# Copyright (C) 2010-2016 GRNET S.A. and individual contributors
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

class AllocatorBase(object):
    def filter_backends(self, backends, vm):
        """The `filter_backends` method takes 2 arguments:
        1. A list of the available backends. A backend is available
        if it is not drained or offline. Each backend is a django object
        and is an instance of the `Backend` model.
        2. A map with 3 keys:
            - `ram`: The size of the memory we want to allocate
            on the backend.
            - `disk`: The size of the disk we want to allocate
            on the backend.
            - `cpu`: The size of the CPU we want to allocate
            on the backend.

        The `Backend` model instances are not locked in the database
        so changing their attributes is not advised. The `filter_backends`
        method should treat the instances as "Read Only".

        """
        raise NotImplementedError(
            'The implementation of `filter_backends` is required.'
        )

    def allocate(self, backends, vm):
        """The `allocate` method takes 2 arguments:
        1. A list of the available backends. A backend is available
        if it is not drained or offline. Each backend is a django object
        and is an instance of the `Backend` model.
        2. A map with 3 keys:
            - `ram`: The size of the memory we want to allocate
            on the backend.
            - `disk`: The size of the disk we want to allocate
            on the backend.
            - `cpu`: The size of the CPU we want to allocate
            on the backend.
        The `Backend` model instances are now locked in the database.
        Be warned that some attributes of the backends that were given
        on the `filter_backends` function may have changed, so it is suggested
        you double check the backends.

        """
        raise NotImplementedError(
            'The implementation of `allocate` is required'
        )
