#
# Credit Allocator - Administration script
#
# Execute once to increase user credits according to their monthly rate
#
# Copyright 2010 Greek Research and Technology Network
#

from db.models import *

from django.db.models import F

# main entry point
def allocate_credit():
    """Refund user with credits"""
    
    # Select the users that their monthly
    user_list = OceanUser.objects.filter(credit__lt=F('quota'))
    
    if len(user_list) == 0:
        print "No users found"
        return

    for user in user_list:
        user.allocate_credits()
        print "Add %d credits to %s. Total: %d" % ( user.monthly_rate, user.name, user.credit )
        user.save()
