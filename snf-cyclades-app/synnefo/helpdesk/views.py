from django.shortcuts import redirect
from django.views.generic.simple import direct_to_template
from synnefo.db.models import *

def index(request):
    """
    Helpdesk index view.
    """
    # if form submitted redirect to details
    account = request.GET.get('account', None)
    if account:
      return redirect('synnefo.helpdesk.views.account', account=account)

    # show index template
    return direct_to_template(request, "helpdesk/index.html")


def account(request, account):
    """
    Account details view
    """
    vms = VirtualMachine.objects.filter().order_by('deleted')
    networks = Network.objects.filter().order_by('state')
    user_context = {
        'vms': vms,
        'account': account,
        'networks': networks,
    }
    return direct_to_template(request, "helpdesk/account.html",
        extra_context=user_context)

