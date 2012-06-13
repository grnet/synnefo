from django.shortcuts import redirect
from django.views.generic.simple import direct_to_template
from django.db.models import get_apps
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from synnefo.db.models import *
from synnefo.lib.astakos import get_user, get_token_from_cookie


# TODO: here we mix ui setting with helpdesk
# if sometime in the future helpdesk gets splitted from the
# cyclades api code this should change and helpdesk should provide
# its own setting.
HELPDESK_AUTH_COOKIE = getattr(settings, 'UI_AUTH_COOKIE_NAME', '_pithos2_a')

def helpdesk_user_required(func, groups=['helpdesk']):
    """
    Django view wrapper that checks if identified request user has helpdesk
    permissions (exists in helpdesk group)
    """
    def wrapper(request, *args, **kwargs):
        token = get_token_from_cookie(request, HELPDESK_AUTH_COOKIE)
        get_user(request, settings.ASTAKOS_URL, fallback_token=token)
        if request.user:
            groups = request.user.get('groups', [])
            for g in groups:
                if not g in groups:
                    raise PermissionDenied
        else:
            raise PermissionDenied

        return func(request, *args, **kwargs)

    return wrapper


@helpdesk_user_required
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


@helpdesk_user_required
def account(request, account):
    """
    Account details view.
    """

    # all user vms
    vms = VirtualMachine.objects.filter(userid=account).order_by('deleted')

    # return all user private and public networks
    netfilters = Q(userid=account, public=False) | Q(public=True)
    networks = Network.objects.filter(netfilters).order_by('state')

    user_context = {
        'vms': vms,
        'account': account,
        'networks': networks,
    }
    return direct_to_template(request, "helpdesk/account.html",
        extra_context=user_context)

