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
from django.core.management import setup_environ

import sys
import os

# Discover the path for the Synnefo project.
#
# IMPORTANT:
# This assumes this script has been *linked* into the /etc/ganeti/hooks
# directory on the master and nodes, and that it lives in a ganeti/ directory
# under the Synnefo project root.

try:
    target = os.readlink(sys.argv[0])
except OSError:
    target = sys.argv[0]
target_script = os.path.abspath(target)
target_dirname = os.path.dirname(target_script)

if os.path.split(target_dirname)[1] != "ganeti":
    raise Exception, "Unexpected location for the Synnefo Ganeti hook, " \
        "cannot determine Synnefo project root.\n" \
        "This script run as: %s\nLocation determined to be at: %s\n" \
        "Script in %s, not under ganeti/ directory." % \
        (sys.argv[0], target_script, target_dirname)

# Add the parent of the project root to sys.path (for Python imports),
# then load Django settings.
# FIXME: Why do import references start at synnefo.* ?
synnefo_project_root = os.path.split(target_dirname)[0]
sys.path.append(os.path.join(synnefo_project_root, '..'))

import synnefo.settings as settings
setup_environ(settings)

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
    ("instance-stop", "post"): PostStopHook
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
