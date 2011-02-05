#
# bill Calculator Command - Management Script
#
# Copyright 2010 Greek Research and Technology Network
#

from django.core.management.base import NoArgsCommand

from db import bill_calculator

class Command(NoArgsCommand):
    help = ''
    
    def handle_noargs(self, **options):
        bill_calculator.calculate_bills()