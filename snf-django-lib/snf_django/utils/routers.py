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

"""
Router for the Astakos/Cyclades app. It is used to specify which database will
be used for each model.
"""

from snf_django.utils.db import select_db


class SynnefoRouter(object):

    """Router for Astakos/Cyclades models."""

    def db_for_read(self, model, **hints):
        """Select db to read."""
        app = model._meta.app_label
        return select_db(app)

    def db_for_write(self, model, **hints):
        """Select db to write."""
        app = model._meta.app_label
        return select_db(app)

    # The rest of the methods are ommited since relations and syncing should
    # not affect the router.
