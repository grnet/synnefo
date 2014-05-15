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
Alembic migration wrapper for pithos backend database.

- Locate alembic.ini in backends/lib/sqlalchemy package and pass it
  as parameter to alembic

e.g::

    $ pithos-migrate upgrade head

"""

import sys
import os

from alembic.config import main as alembic_main, Config
from alembic import context, command

from pithos.backends.lib import sqlalchemy as sqlalchemy_backend
from pithos.backends.lib.sqlalchemy import (node, groups, public, xfeatures,
                                            quotaholder_serials)

os.environ['DJANGO_SETTINGS_MODULE'] = 'synnefo.settings'

try:
    # pithos-app case
    from synnefo.settings import PITHOS_BACKEND_DB_CONNECTION
except ImportError:
    try:
        # plankton case
        from synnefo.settings import BACKEND_DB_CONNECTION as \
            PITHOS_BACKEND_DB_CONNECTION
    except ImportError:
        PITHOS_BACKEND_DB_CONNECTION = None

import sqlalchemy as sa

DEFAULT_ALEMBIC_INI_PATH = os.path.join(
    os.path.abspath(os.path.dirname(sqlalchemy_backend.__file__)),
    'alembic.ini')


def initialize_db(dbconnection):
    alembic_cfg = Config(DEFAULT_ALEMBIC_INI_PATH)

    db = alembic_cfg.get_main_option("sqlalchemy.url", dbconnection)
    alembic_cfg.set_main_option("sqlalchemy.url", db)

    engine = sa.engine_from_config(
        alembic_cfg.get_section(alembic_cfg.config_ini_section),
        prefix='sqlalchemy.')

    node.create_tables(engine)
    groups.create_tables(engine)
    public.create_tables(engine)
    xfeatures.create_tables(engine)
    quotaholder_serials.create_tables(engine)

    # then, load the Alembic configuration and generate the
    # version table, "stamping" it with the most recent rev:
    command.stamp(alembic_cfg, "head")


def main(argv=None, **kwargs):
    if not argv:
        argv = sys.argv

    # clean up args
    argv.pop(0)

    if len(argv) >= 1 and argv[0] == 'initdb':
        print "Initializing db."
        initialize_db(PITHOS_BACKEND_DB_CONNECTION)
        print "DB initialized."
        exit(1)

    # default config arg, if not already set
    if not '-c' in argv:
        argv.insert(0, DEFAULT_ALEMBIC_INI_PATH)
        argv.insert(0, '-c')

    alembic_main(argv, **kwargs)
if __name__ == '__main__':
    import sys
    main(sys.argv)
