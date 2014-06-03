# Copyright (C) 2014 GRNET S.A.
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

from .common import CommonMixin
from .delete_by_uuid import TestDeleteByUUIDMixin


class TestSQLAlchemyBackend(CommonMixin, TestDeleteByUUIDMixin):
    db_module = 'pithos.backends.lib.sqlalchemy'
    db_connection = 'sqlite:////tmp/test_pithos_backend.db'

class TestSQLiteBackend(CommonMixin, TestDeleteByUUIDMixin):
        db_module = 'pithos.backends.lib.sqlite'
        db_connection = ':memory:'
