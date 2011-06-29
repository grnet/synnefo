#!/usr/bin/env python
#
# Copyright (c) 2010 Greek Research and Technology Network
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
