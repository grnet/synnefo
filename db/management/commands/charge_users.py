#
# Charge Users Command - Management Script
#
# Copyright 2010 Greek Research and Technology Network
#

from django.core.management.base import NoArgsCommand

from db import charger

class Command(NoArgsCommand):
    help = 'Charge the users for VM usage'
    
    def handle_noargs(self, **options):
        charger.periodically_charge()
