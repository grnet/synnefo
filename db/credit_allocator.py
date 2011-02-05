#
# Credit Allocator - Administration script
#
# Execute once to increase user credits according to their monthly rate
#
# Copyright 2010 Greek Research and Technology Network
#

from db.models import *
from django.db.models import F
from datetime import datetime

import logging


# main entry point
def allocate_credit():
    """Refund user with credits"""
    logging.basicConfig(level=logging.DEBUG)
    
    logging.info('Credit Allocation administration script is running')
    logging.info('Time: %s' % ( datetime.now().isoformat(), ))
    
    # Select the users that their monthly
    user_list = OceanUser.objects.filter(credit__lt=F('quota'))
    
    if len(user_list) == 0:
        logging.warning('No users found')
    else:
        logging.info('Found %d user(s)' % ( len(user_list), ))

    for user in user_list:
        user.allocate_credits()
        logging.info("Adding %d credits to %s. Total: %d" % ( user.monthly_rate, user.name, user.credit ))
        user.save()
