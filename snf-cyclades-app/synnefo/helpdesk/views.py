from itertools import chain

from django.shortcuts import redirect
from django.views.generic.simple import direct_to_template
from django.db.models import get_apps
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.utils import simplejson as json
from urllib import unquote

from synnefo.lib.astakos import get_user
from synnefo.db.models import *

def get_token_from_cookie(request, cookiename):
    """
    Extract token from the cookie name provided. Cookie should be in the same
    form as astakos service sets its cookie contents::

        <user_uniq>|<user_token>
    """
    try:
        cookie_content = unquote(request.COOKIES.get(cookiename, None))
        return cookie_content.split("|")[1]
    except AttributeError:
        pass

    return None

# TODO: here we mix ui setting with helpdesk settings
# if sometime in the future helpdesk gets splitted from the
# cyclades api code this should change and helpdesk should provide
# its own setting HELPDESK_AUTH_COOKIE_NAME.
HELPDESK_AUTH_COOKIE = getattr(settings, 'UI_AUTH_COOKIE_NAME', '_pithos2_a')

def helpdesk_user_required(func, groups=['helpdesk']):
    """
    Django view wrapper that checks if identified request user has helpdesk
    permissions (exists in helpdesk group)
    """
    def wrapper(request, *args, **kwargs):
        return func(request, *args, **kwargs)
        token = get_token_from_cookie(request, HELPDESK_AUTH_COOKIE)
        get_user(request, settings.ASTAKOS_URL, fallback_token=token)
        if hasattr(request, 'user') and request.user:
            groups = request.user.get('groups', [])

            if not groups:
                raise PermissionDenied

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
    public_networks = Network.objects.filter(public=True).order_by('state')
    private_networks = Network.objects.filter(userid=account).order_by('state')
    networks = list(public_networks) + list(private_networks)
        
    account_exists = True
    if vms.count() == 0 and private_networks.count() == 0:
        account_exists = False

    user_context = {
        'account_exists': account_exists,
        'account': account,
        'vms': vms,
        'networks': networks,
        'UI_MEDIA_URL': settings.UI_MEDIA_URL
    }
    return direct_to_template(request, "helpdesk/account.html",
        extra_context=user_context)


@helpdesk_user_required
def user_list(request):
    """
    Return a json list of users based on the prefix provided. Prefix
    should end with "@".
    """

    prefix = request.GET.get('prefix', None)
    if not prefix or "@" not in prefix:
        raise Http404

    # keep only the user part (e.g. "user@")
    prefix = prefix.split("@")[0] + "@"

    q = Q(userid__startswith=prefix) & ~Q(userid=None)
    vm_users = VirtualMachine.objects.filter(q).values_list("userid", flat=True)
    net_users = Network.objects.filter(q).values_list("userid", flat=True)
    users = list(set(list(vm_users) + list(net_users)))
    return HttpResponse(json.dumps(users), content_type="application/json")

