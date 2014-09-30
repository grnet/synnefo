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

NS = "ns"
DB = "db"
MQ = "mq"
ASTAKOS = "astakos"
CYCLADES = "cyclades"
ADMIN = "admin"
PITHOS = "pithos"
CLIENT = "client"
ROUTER = "router"
NFS = "nfs"
CMS = "cms"
STATS = "stats"
CLUSTERS = "clusters"
MASTER = "master"
VMC = "vmc"
DEV = "dev"
BACKEND = "backend"

VALUE_OK = "ok"
STATUS_FILE = "snf_deploy_status"

DEFAULT_NODE = None
DEFAULT_CLUSTER = None
DEFAULT_SETUP = "auto"
DUMMY_NODE = "dummy"

CERT_OVERRIDE = "cert_override.txt"
CERT_PATH = "/etc/ssl/certs/ssl-cert-snakeoil.pem"

DEFAULT_PASSWD_LENGTH = 10

DB_PASSWD = "synnefo_db_passwd"
RAPI_PASSWD = "synnefo_rapi_passwd"
MQ_PASSWD = "synnefo_rabbitmq_passwd"
VNC_PASSWD = "synnefo_vnc_passwd"
CYCLADES_SECRET = "cyclades_secret"
OA2_SECRET = "oa2_secret"
WEBPROJECT_SECRET = "webproject_secret"
STATS_SECRET = "stats_secret"
COLLECTD_SECRET = "collectd_secret"

# This is used for generating random passwords
ALL_PASSWDS_AND_SECRETS = frozenset([
    DB_PASSWD, RAPI_PASSWD, MQ_PASSWD,
    CYCLADES_SECRET, OA2_SECRET, WEBPROJECT_SECRET, STATS_SECRET,
    COLLECTD_SECRET, VNC_PASSWD
    ])

EXTERNAL_PUBLIC_DNS = "8.8.8.8"
