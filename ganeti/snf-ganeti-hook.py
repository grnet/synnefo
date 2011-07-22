#!/usr/bin/env python
#
# -*- coding: utf-8 -*-
#
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
#
"""Ganeti hook for Synnefo

This is the generic Synnefo Ganeti hook.

It uses the full path of the hook, as passed through sys.argv[0]
to discover the root of the Synnefo project, then passes
control to the function which implements this specific hook,
based on the GANETI_HOOKS_PATH and GANETI_HOOKS_PHASE env variables,
set by Ganeti.

"""
import logging

import sys
import os

# IMPORTANT: PYTHONPATH must contain the parent of the Synnefo project root.
try:
    import synnefo.settings as settings
except ImportError:
    raise Exception("Cannot import settings, make sure PYTHONPATH contains "
                    "the parent directory of the Synnefo Django project.")

# A hook runs either in the "pre" or "post" phase of a Ganeti operation.
# Possible values for the Ganeti operation are "instance-start",
# "instance-stop", "instance-reboot", "instance-modify". See the Ganeti
# documentation for a full list.

# The operation and phase for which the hook run are determined from the
# values of the GANETI_HOOK_PATH and GANETI_HOOK_PHASE environment variables.
# For each valid (operation, phase) pair control passes to the corresponding
# Python function, based on the following dictionary.

from synnefo.ganeti.hooks import \
    PostStartHook, PostStopHook

hooks = {
    ("instance-add", "post"): PostStartHook,
    ("instance-start", "post"): PostStartHook,
    ("instance-reboot", "post"): PostStartHook,
    ("instance-stop", "post"): PostStopHook,
    ("instance-modify", "post"): PostStartHook
}

def main():
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("synnefo.ganeti")

    try:
        instance = os.environ['GANETI_INSTANCE_NAME']
        op = os.environ['GANETI_HOOKS_PATH']
        phase = os.environ['GANETI_HOOKS_PHASE']
    except KeyError:
        raise Exception("Environment missing one of: " \
            "GANETI_INSTANCE_NAME, GANETI_HOOKS_PATH, GANETI_HOOKS_PHASE")

    prefix = instance.split('-')[0]

    # FIXME: The hooks should only run for Synnefo instances.
    # Uncomment the following lines for a shared Ganeti deployment.
    # Currently, the following code is commented out because multiple
    # backend prefixes are used in the same Ganeti installation during development.
    #if not instance.startswith(settings.BACKEND_PREFIX_ID):
    #    logger.warning("Ignoring non-Synnefo instance %s", instance)
    #    return 0

    try:
        hook = hooks[(op, phase)](logger, os.environ, instance, prefix)
    except KeyError:
        raise Exception("No hook found for operation = '%s', phase = '%s'" % (op, phase))
    return hook.run()


if __name__ == "__main__":
    sys.exit(main())

# vim: set ts=4 sts=4 sw=4 et ai :
