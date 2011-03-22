#
# Various utility functions
#
# Copyright 2010 Greek Research and Technology Network
#
from django.conf import settings

from db.models import VirtualMachine

def id_from_instance_name(name):
    """Returns VirtualMachine's Django id, given a ganeti machine name.

    Strips the ganeti prefix atm. Needs a better name!

    """
    if not str(name).startswith(settings.BACKEND_PREFIX_ID):
        raise VirtualMachine.InvalidBackendIdError(str(name))
    ns = str(name).lstrip(settings.BACKEND_PREFIX_ID)
    if not ns.isdigit():
        raise VirtualMachine.InvalidBackendIdError(str(name))

    return int(ns)
