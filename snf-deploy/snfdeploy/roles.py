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

from snfdeploy import constants
from snfdeploy import components


_ROLE_MAP = {
    constants.NS: components.NS,
    constants.NFS: components.NFS,
    constants.DB: components.DB,
    constants.MQ: components.MQ,
    constants.ASTAKOS: components.Astakos,
    constants.CYCLADES: components.Cyclades,
    constants.ADMIN: components.Admin,
    constants.PITHOS: components.Pithos,
    constants.CMS: components.CMS,
    constants.STATS: components.Stats,
    constants.MASTER: components.Master,
    constants.VMC: components.VMC,
    constants.CLIENT: components.Client,
    constants.DEV: components.GanetiDev,
    constants.ROUTER: components.Router,
    }


def _get_role_map(role):
    if role in _ROLE_MAP:
        return _ROLE_MAP[role]
    else:
        return getattr(components, role)


def get(role, ctx):
    assert role and ctx
    c = _get_role_map(role)
    ctx.role = role
    return c(ctx=ctx)
