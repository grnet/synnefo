# Copyright 2011 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.

# Business Logic for all Credit related activity

from datetime import datetime
from django.db import transaction

from synnefo.db.models import Debit, FlavorCost

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
    if vm.operstate in charged_states:
        cost_list = []

        # remember, we charge only for Started and Stopped
        if vm.operstate == 'STARTED':
            cost_list = get_cost_active(vm.flavor, start_datetime, vm.charged)
        elif vm.operstate == 'STOPPED':
            cost_list = get_cost_inactive(vm.flavor, start_datetime, vm.charged)

        # find the total vost
        total_cost = sum([x[1] for x in cost_list])

        # add the debit entry
        description = "Server = %s, charge = %d for state: %s" % (vm.name, total_cost, vm.operstate)
        debit_account(vm.owner, total_cost, vm, description)

    vm.save()


def get_costs(vm, start_datetime, end_datetime, active):
    """Return a list with FlavorCost objects for the specified duration"""
    def between(enh_fc, a_date):
        """Checks if a date is between a FlavorCost duration"""
        if enh_fc.effective_from <= a_date and enh_fc.effective_to is None:
            return True

        return enh_fc.effective_from <= a_date and enh_fc.effective_to >= a_date

    # Get the related FlavorCost objects, sorted.
    price_list = FlavorCost.objects.filter(flavor=vm).order_by('effective_from')

    # add the extra field FlavorCost.effective_to
    for idx in range(0, len(price_list)):
        if idx + 1 == len(price_list):
            price_list[idx].effective_to = None
        else:
            price_list[idx].effective_to = price_list[idx + 1].effective_from

    price_result = []
    found_start = False

    # Find the affected FlavorCost, according to the
    # dates, and put them in price_result
    for p in price_list:
        if between(p, start_datetime):
            found_start = True
            p.effective_from = start_datetime
        if between(p, end_datetime):
            p.effective_to = end_datetime
            price_result.append(p)
            break
        if found_start:
            price_result.append(p)

    results = []

    # Create the list and the result tuples
    for p in price_result:
        if active:
            cost = p.cost_active
        else:
            cost = p.cost_inactive

        results.append( ( p.effective_from, calculate_cost(p.effective_from, p.effective_to, cost)) )

    return results


def calculate_cost(start_date, end_date, cost):
    """Calculate the total cost for the specified duration"""
    td = end_date - start_date
    sec = float(td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / float(10**6)
    total_hours = float(sec) / float(60.0*60.0)
    total_cost = float(cost)*total_hours

    return round(total_cost)


def get_cost_active(vm, start_datetime, end_datetime):
    """Returns a list with the active costs for the specified duration"""
    return get_costs(vm, start_datetime, end_datetime, True)


def get_cost_inactive(vm, start_datetime, end_datetime):
    """Returns a list with the inactive costs for the specified duration"""
    return get_costs(vm, start_datetime, end_datetime, False)
