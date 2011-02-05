#
# Credit Allocator Command - Management Script
#
# Invokes credit allocator from manage.py
#
# Copyright 2010 Greek Research and Technology Network
#

from django.core.management.base import NoArgsCommand

from db import credit_allocator

class Command(NoArgsCommand):
    help = 'Infuse user with their monthly rate credits'
    
    def handle_noargs(self, **options):
        credit_allocator.allocate_credit()
        return