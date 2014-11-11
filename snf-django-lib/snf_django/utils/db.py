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

from django.conf import settings

ASTAKOS_DATABASE = "astakos"
CYCLADES_DATABASE = "cyclades"
SYNNEFO_ROUTER = "snf_django.utils.routers.SynnefoRouter"


def select_db(app):
    """Database selection based on the provided app and database settings.

    This function takes as argument a Synnefo app name and returns the database
    where its models are stored. Commonly, if this function is called from
    astakos code, the provided app name should be "im". Likewise, if this
    function is called from cyclades code, the app name should be "db".
    """
    routers = getattr(settings, "DATABASE_ROUTERS", [])
    if not routers or SYNNEFO_ROUTER not in settings.DATABASE_ROUTERS:
        return "default"

    if (app in ["im", "auth", "quotaholder_app"] and
            ASTAKOS_DATABASE in settings.DATABASES):
        return ASTAKOS_DATABASE
    elif app == "db" and CYCLADES_DATABASE in settings.DATABASES:
        return CYCLADES_DATABASE
    return "default"
