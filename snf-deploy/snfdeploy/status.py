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
from snfdeploy import filelocker
from snfdeploy.lib import create_passwd

status = sys.modules[__name__]


def _lock_read_write(fn):
    def wrapper(*args, **kwargs):
        with filelocker.lock(status.lockfile, filelocker.LOCK_EX):
            status.cfg.read(status.statusfile)
            ret = fn(*args, **kwargs)
            if config.force or not config.dry_run:
                with open(status.statusfile, 'wb') as configfile:
                    status.cfg.write(configfile)
        return ret
    return wrapper


def _create_section(section):
    if not status.cfg.has_section(section):
        status.cfg.add_section(section)


@_lock_read_write
def _check(section, option):
    try:
        return status.cfg.get(section, option, True)
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        return None


@_lock_read_write
def _update(section, option, value):
    _create_section(section)
    status.cfg.set(section, option, value)


def get_passwd(setup, target):
    passwd = _check(setup, target)
    if not passwd:
        passwd = create_passwd(constants.DEFAULT_PASSWD_LENGTH)
        _update(setup, target, passwd)
    return passwd


def update(component):
    section = component.node.ip
    option = component.__class__.__name__
    _update(section, option, constants.VALUE_OK)


def check(component):
    section = component.node.ip
    option = component.__class__.__name__
    return _check(section,  option)


def reset():
    try:
        os.remove(status.statusfile)
    except OSError:
        pass


def init():
    status.state_dir = config.state_dir
    status.cfg = ConfigParser.ConfigParser()
    status.cfg.optionxform = str
    status.statusfile = os.path.join(config.state_dir, constants.STATUS_FILE)
    status.lockfile = "%s.lock" % status.statusfile
