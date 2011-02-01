#
# Credit Allocator - Administration script
#
# Execute once to increase user credits according to their monthly rate
#
# Copyright © 2010 Greek Research and Technology Network
#

from db.models import *

from django.db.models import F

import logging

# main entry point
def main():
    """
    This method allocates credits for the users according to their montly rate
    """
    
    # Select the users that their monthly
    user_list = OceanUser.objects.filter(quota__lte=F('credit') + F('monthly_rate'))

    for user in user_list:
        user.allocateCredit()
        logging.info("Add %d credits to %s. Total: %d" % ( user.monthly_rate, user.name, user.credit ))
        user.save()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(main())