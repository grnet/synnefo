#
# Charger - Administration script
#
# Executed hourly to charge vm usage for each user
#
# Copyright 2010 Greek Research and Technology Network
#

from db.models import *


def periodically_charge():
    """Scan all virtual machines and charge each user"""
    all_vms = VirtualMachine.objects.all()
    
    if not len(all_vms):
        print "No virtual machines found"
        return
    
    for vm in all_vms:
        # Running and Stopped is charged, else the cost is zero
        vm.charge()

# vim: set ts=4 sts=4 sw=4 et ai :
