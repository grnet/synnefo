# Copyright 2011 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

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
        print >>sys.stderr, "Failed to list *.conf files under %s" % \
                            SYNNEFO_SETTINGS_DIR
        raise SystemExit(1)
    conffiles.sort()
    for f in conffiles:
        try:
            execfile(os.path.abspath(f))
        except Exception as e:
            print >>sys.stderr, "Failed to read settings file: %s [%s]" % \
                                (os.path.abspath(f), e)
            raise SystemExit(1)
