#
# Callback functions used by the cron dispatcher.
#
# Copyright 2010 Greek Research and Technology Network
#


def send_recons_req():
    """
        Publish a reconsiliation request to the queue
    """

    reconcile = dict()
    reconcile['msg'] = 'reconcile'

    

    pass

def send_credit_calc_req():
    """
        Publish a credit calculation request to the queue
    """
    pass