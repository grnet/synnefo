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


from django.core.management import ManagementUtility
from django.core import management
from synnefo.util.version import get_component_version
from synnefo.lib.dictconfig import dictConfig

# monkey patch to show synnefo version instead of django version
management.get_version = lambda: get_component_version('webproject')

import sys
import os


class SynnefoManagementUtility(ManagementUtility):

    def main_help_text(self):
        return ManagementUtility.main_help_text(self, commands_only=True)


def configure_logging():
    try:
        from synnefo.settings import SNF_MANAGE_LOGGING_SETUP
        dictConfig(SNF_MANAGE_LOGGING_SETUP)
    except ImportError:
        import logging
        logging.basicConfig()
        log = logging.getLogger()
        log.warning("SNF_MANAGE_LOGGING_SETUP setting missing.")


def main():
    os.environ['DJANGO_SETTINGS_MODULE'] = \
        os.environ.get('DJANGO_SETTINGS_MODULE', 'synnefo.settings')
    configure_logging()
    mu = SynnefoManagementUtility(sys.argv)
    mu.execute()

if __name__ == "__main__":
    main()
