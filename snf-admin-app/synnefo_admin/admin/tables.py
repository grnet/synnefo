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

from eztables.views import DatatablesView
from django.utils.html import escape


def escape_row(row):
    """Escape a whole row using Django's escape function."""
    return [escape(cell) for cell in row]


class AdminJSONView(DatatablesView):

    """Class-based Django view for admin purposes.

    It is based on the DataTablesView class of django-eztables plugin and aims
    to provide some common functionality for all the views that are derived
    from it.
    """

    def format_data_rows(self, rows):
        if hasattr(self, 'format_data_row'):
            rows = [escape_row(self.format_data_row(row)) for row in rows]
        else:
            rows = [escape_row(row) for row in rows]
        return rows
