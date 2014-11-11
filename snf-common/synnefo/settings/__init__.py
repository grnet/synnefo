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

import os
import sys

from synnefo.util.entry_points import extend_settings

# set synnefo package __file__ to fix django related bug
import synnefo
synnefo.__file__ = os.path.join(synnefo.__path__[0], '__init__.py')

# import default settings
from synnefo.settings.default import *

# autodetect default settings provided by synnefo applications
extend_settings(__name__, 'synnefo')

# extend default settings with settings provided within *.conf user files
# located in directory specified in the SYNNEFO_SETTINGS_DIR
# environment variable
SYNNEFO_SETTINGS_DIR = os.environ.get('SYNNEFO_SETTINGS_DIR', "/etc/synnefo/")
if os.path.exists(SYNNEFO_SETTINGS_DIR):
    try:
        entries = [os.path.join(SYNNEFO_SETTINGS_DIR, x) for x in
                   os.listdir(SYNNEFO_SETTINGS_DIR)]
        conffiles = [f for f in entries if os.path.isfile(f) and
                     f.endswith(".conf")]
    except Exception as e:
        print >> sys.stderr, "Failed to list *.conf files under %s" % \
                             SYNNEFO_SETTINGS_DIR
        raise SystemExit(1)
    conffiles.sort()
    for f in conffiles:
        try:
            execfile(os.path.abspath(f))
        except Exception as e:
            print >> sys.stderr, "Failed to read settings file: %s [%r]" % \
                                 (os.path.abspath(f), e)
            raise SystemExit(1)


from os import environ
# The tracing code is enabled by an environmental variable and not a synnefo
# setting, on purpose, so that you can easily control whether it'll get loaded
# or not, based on context (eg enable it for gunicorn but not for eventd).
if environ.get('SYNNEFO_TRACE'):
    from synnefo.lib import trace
    trace.set_signal_trap()
