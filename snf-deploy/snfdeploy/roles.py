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

from snfdeploy.components import *

ROLES = {
    "ns": [HW, SSH, DDNS, NS, DNS, APT],
    "db": [HW, SSH, DNS, APT, DB],
    "mq": [HW, SSH, DNS, APT, MQ],
    "nfs": [HW, SSH, DNS, APT, NFS],
    "astakos": [HW, SSH, DNS, APT, Apache, Gunicorn, Common, WEB, Astakos],
    "pithos": [
        HW, SSH, DNS, APT, Apache,
        Gunicorn, Common, WEB, PithosBackend, Archip, Pithos
        ],
    "cyclades": [
        HW, SSH, DNS, APT,
        Apache, Gunicorn, Common, WEB, Cyclades, VNC, PithosBackend, Archip
        ],
    "cms": [HW, SSH, DNS, APT, Apache, Gunicorn, Common, WEB, CMS],
    "stats": [
        HW, SSH, DNS, APT,
        Apache, Gunicorn, Common, WEB, Collectd, Stats
        ],
    "client": [HW, SSH, DNS, APT, Kamaki, Burnin],
    "ganeti": [
        HW, SSH, DNS, DDNS, APT, Mount,
        Ganeti, ExtStorage, PithosBackend, Archip, ArchipGaneti,
        Image, Network, GTools, GanetiCollectd,
        ],
    "master": [
        HW, SSH, DNS, DDNS, APT, Mount,
        Ganeti, ExtStorage, Master, PithosBackend, Archip, ArchipGaneti,
        Image, Network, GTools, GanetiCollectd,
        ],
    }

CONFLICTS = {
    Mount: [NFS],
    CMS: [Astakos, Pithos, Cyclades]
    }
