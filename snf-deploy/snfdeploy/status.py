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

import ConfigParser
import os
import sys
from snfdeploy import constants
from snfdeploy import config

status = sys.modules[__name__]


def check(ip, component_class):
    try:
        return status.cfg.get(ip, component_class.__name__, True)
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        return None


def update(ip, component_class, stat):
    if not status.cfg.has_section(ip):
        status.cfg.add_section(ip)
    status.cfg.set(ip, component_class.__name__, stat)


def write():
    with open(status.statusfile, 'wb') as configfile:
        status.cfg.write(configfile)


def init():
    status.state_dir = config.state_dir
    status.cfg = ConfigParser.ConfigParser()
    status.cfg.optionxform = str
    status.statusfile = os.path.join(config.state_dir, constants.STATUS_FILE)
    status.cfg.read(status.statusfile)
