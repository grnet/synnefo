#
# Business Logic for all Credit related activity
#
# Copyright 2010 Greek Research and Technology Network
#

from datetime import datetime

from db.models import Debit
from django.db import transaction

@transaction.commit_on_success
def debit_account(user , amount, vm, description):
    """Charges the user with the specified amount of credits for a vm (resource)"""
    date_now = datetime.now()
    user.credit = user.credit - amount
    user.save()

    # then write the debit entry
    debit = Debit()
    debit.user = user
    debit.vm = vm
    debit.when = date_now
    debit.description = description
    debit.save()


@transaction.commit_on_success
def credit_account(self, amount, creditor, description):
    """No clue :)"""
    return


@transaction.commit_on_success
def charge(vm):
    """Charges the owner of this VM.

    Charges the owner of a VM for the period
    from vm.charged to datetime.now(), based on the
    current operating state.

    """
    charged_states = ('STARTED', 'STOPPED')

    start_datetime = vm.charged
    vm.charged = datetime.now()

    # Only charge for a specific set of states
    if vm._operstate in charged_states:
        cost_list = []

        # remember, we charge only for Started and Stopped
        if vm._operstate == 'STARTED':
            cost_list = vm.flavor.get_cost_active(start_datetime, vm.charged)
        elif vm._operstate == 'STOPPED':
            cost_list = vm.flavor.get_cost_inactive(start_datetime, vm.charged)

        # find the total vost
        total_cost = sum([x[1] for x in cost_list])

        # add the debit entry
        description = "Server = %s, charge = %d for state: %s" % (vm.name, total_cost, vm._operstate)
        debit_account(vm.owner, total_cost, vm, description)

    vm.save()
