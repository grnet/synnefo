#
# Credit Allocator Command - Management Script
#
# Copyright 2010 Greek Research and Technology Network
#

from django.core.management.base import NoArgsCommand

from synnefo.db import credit_allocator

class Command(NoArgsCommand):
    help = 'Add credits to users according to their monthly rate'
    
    def handle_noargs(self, **options):
        credit_allocator.allocate_credit()