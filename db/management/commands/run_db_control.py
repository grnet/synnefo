#
# Run DB Control Command - Management Script
#
# Copyright 2010 Greek Research and Technology Network
#

from django.core.management.base import NoArgsCommand

from db import db_controller

class Command(NoArgsCommand):
    help = ''
    
    def handle_noargs(self, **options):
        db_controller.main()