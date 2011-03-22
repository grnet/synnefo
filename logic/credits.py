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
    date_now = datetime.datetime.now()
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
