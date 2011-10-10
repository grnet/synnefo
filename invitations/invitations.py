# vim: set fileencoding=utf-8 :
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


from datetime import timedelta
import datetime
import base64
import urllib
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, \
    HttpResponseBadRequest, HttpResponseServerError
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.core.validators import validate_email
from django.views.decorators.csrf import csrf_protect
from django.utils.translation import ugettext as _

from synnefo.logic.email_send import send_async, send
from synnefo.api.common import method_not_allowed
from synnefo.db.models import Invitations, SynnefoUser
from synnefo.logic import users
from synnefo.util import log

from Crypto.Cipher import AES

_logger = log.getLogger("synnefo.invitations")


def process_form(request):
    errors = []
    valid_inv = filter(lambda x: x.startswith("name_"), request.POST.keys())
    invitation = None

    for inv in valid_inv:
        (name, inv_id) = inv.split('_')

        email = ""
        name = ""
        try:
            email = request.POST['email_' + inv_id]
            name = request.POST[inv]

            validate_name(name)
            validate_email(email)

            invitation = add_invitation(request.user, name, email)
            send_invitation(invitation)

        except (InvitationException, ValidationError) as e:
            errors += ["Invitation to %s <%s> not sent. Reason: %s" %
                       (name, email, e.messages[0])]
        except Exception as e:
            remove_invitation(invitation)
            _logger.exception(e)
            errors += ["Invitation to %s <%s> could not be sent. An unexpected"
                       " error occurred. Please try again later." %
                       (name, email)]

    response = None
    if errors:
        data = render_to_string('invitations.html',
                                {'invitations':
                                     invitations_for_user(request),
                                 'errors':
                                     errors,
                                 'invitations_left':
                                     get_invitations_left(request.user)},
                                context_instance=RequestContext(request))
        response = HttpResponse(data)
        _logger.warn("Error adding invitation %s -> %s: %s" %
                     (request.user.uniq, email, errors))
    else:
        # form submitted
        data = render_to_string('invitations.html',
                                {'invitations':
                                    invitations_for_user(request),
                                 'invitations_left':
                                    get_invitations_left(request.user)},
                                context_instance=RequestContext(request))
        response = HttpResponse(data)
        _logger.info("Added invitation %s -> %s" % (request.user.uniq, email))

    return response


def validate_name(name):
    if name is None or name.strip() == '':
        raise ValidationError("Name is empty")

    if name.find(' ') is -1:
        raise ValidationError(_("Name must contain at least one space"))

    return True


def invitations_for_user(request):
    invitations = []

    for inv in Invitations.objects.filter(source=request.user).order_by("-id"):
        invitation = {}

        invitation['sourcename'] = inv.source.realname
        invitation['source'] = inv.source.uniq
        invitation['targetname'] = inv.target.realname
        invitation['target'] = inv.target.uniq
        invitation['accepted'] = inv.accepted
        invitation['sent'] = inv.created
        invitation['id'] = inv.id

        invitations.append(invitation)

    return invitations


@csrf_protect
def inv_demux(request):

    if request.method == 'GET':
        data = render_to_string('invitations.html',
                                {'invitations':
                                     invitations_for_user(request),
                                 'invitations_left':
                                     get_invitations_left(request.user)},
                                context_instance=RequestContext(request))
        return HttpResponse(data)
    elif request.method == 'POST':
        return process_form(request)
    else:
        method_not_allowed(request)


def login(request):

    if not request.method == 'GET':
        method_not_allowed(request)

    key = request.GET.get('key', None)

    if key is None:
        return render_login_error("10", "Required key is missing")

    PADDING = '{'

    try:
        DecodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(PADDING)
        cipher = AES.new(settings.INVITATION_ENCR_KEY)
        decoded = DecodeAES(cipher, key)
    except Exception:
        return render_login_error("20", "Required key is invalid")

    users = SynnefoUser.objects.filter(auth_token=decoded)

    if users.count() is 0:
        return render_login_error("20", "Required key is invalid")

    user = users[0]
    invitations = Invitations.objects.filter(target=user)

    if invitations.count() is 0:
        return render_login_error("30", "Non-existent invitation")

    inv = invitations[0]

    valid = timedelta(days=settings.INVITATION_VALID_DAYS)
    valid_until = inv.created + valid
    now = datetime.datetime.now()

    if now > valid_until:
        return render_login_error("40",
                                  "Invitation has expired (was valid until " \
                                  "%s, now is %s" %
                                  (valid_until.strftime('%A, %d %B %Y'),
                                   now.strftime('%A, %d %B %Y')))

    # Since the invitation is valid, renew the user's auth token. This also
    # takes care of cases where the user re-uses the invitation to
    # login when the original token has expired
    from synnefo.logic import users   # redefine 'users'
    users.set_auth_token_expires(user, valid_until)

    #if inv.accepted == False:
    #    return render_login_error("60", "Invitation already accepted")

    inv.accepted = True
    inv.save()

    _logger.info("Invited user %s logged in", inv.target.uniq)

    data = dict()
    data['user'] = user.realname
    data['url'] = settings.APP_INSTALL_URL

    welcome = render_to_string('welcome.html', {'data': data})

    response = HttpResponse(welcome)

    response.set_cookie('X-Auth-Token',
                        value=user.auth_token,
                        expires=valid_until.strftime('%a, %d-%b-%Y %H:%M:%S %Z'),
                        path='/')
    response['X-Auth-Token'] = user.auth_token
    return response


def render_login_error(code, text):
    error = dict()
    error['id'] = code
    error['text'] = text

    data = render_to_string('error.html', {'error': error})

    response = HttpResponse(data)
    return response


def send_invitation(invitation):
    email = {}
    email['invitee'] = invitation.target.realname
    email['inviter'] = invitation.source.realname

    valid = timedelta(days=settings.INVITATION_VALID_DAYS)
    valid_until = invitation.created + valid
    email['valid_until'] = valid_until.strftime('%A, %d %B %Y')
    email['url'] = enconde_inv_url(invitation)

    data = render_to_string('invitation.txt', {'email': email})

    _logger.debug("Invitation URL: %s" % email['url'])

    # send_async(
    #    frm = "%s"%(settings.DEFAULT_FROM_EMAIL),
    #    to = "%s <%s>"%(invitation.target.realname,invitation.target.uniq),
    #    subject = _('Invitation to ~okeanos IaaS service'),
    #    body = data
    #)
    send(recipient="%s <%s>" % (invitation.target.realname,
                                invitation.target.uniq),
         subject=_('Invitation to ~okeanos IaaS service'),
         body=data)


def enconde_inv_url(invitation):
    PADDING = '{'
    pad = lambda s: s + (32 - len(s) % 32) * PADDING
    EncodeAES = lambda c, s: base64.b64encode(c.encrypt(pad(s)))

    cipher = AES.new(settings.INVITATION_ENCR_KEY)
    encoded = EncodeAES(cipher, invitation.target.auth_token)

    url_safe = urllib.urlencode({'key': encoded})
    url = settings.APP_INSTALL_URL + "/invitations/login?" + url_safe

    return url


def resend(request):
    """
    Resend an invitation that has been already sent
    """

    if not request.method == 'POST':
        return method_not_allowed(request)

    invid = request.POST["invid"]

    matcher = re.compile('^[0-9]+$')

    # XXX: Assumes numeric DB keys
    if not matcher.match(invid):
        return HttpResponseBadRequest("Invalid content for parameter [invid]")

    try:
        inv = Invitations.objects.get(id=invid)
    except Exception:
        return HttpResponseBadRequest("Invitation to resend does not exist")

    if not request.user == inv.source:
        return HttpResponseBadRequest("Invitation does not belong to user")

    try:
        send_invitation(inv)
    except Exception as e:
        _logger.exception(e)
        return HttpResponseServerError("Error sending invitation email")

    return HttpResponse("Invitation has been resent")


def get_invitee_level(source):
    return get_user_inv_level(source) + 1


def get_user_inv_level(u):
    inv = Invitations.objects.filter(target=u)

    if not inv:
        raise Exception("User without invitation", u)

    return inv[0].level


@transaction.commit_on_success
def add_invitation(source, name, email):
    """
        Adds an invitation, if the source user has not gone over his/her
        invitation limit or the target user has not been invited already
    """
    num_inv = Invitations.objects.filter(source=source).count()

    if num_inv >= source.max_invitations:
        raise TooManyInvitations("User invitation limit (%d) exhausted" %
                                 source.max_invitations)

    target = SynnefoUser.objects.filter(uniq=email)

    if target.count() is not 0:
        raise AlreadyInvited("User with email %s already invited" % (email))

    users.register_user(name, email)

    target = SynnefoUser.objects.filter(uniq=email)

    r = list(target[:1])
    if not r:
        raise Exception("Invited user cannot be added")

    u = target[0]
    invitee_level = get_invitee_level(source)

    u.max_invitations = settings.INVITATIONS_PER_LEVEL[invitee_level]
    u.save()

    inv = Invitations()
    inv.source = source
    inv.target = u
    inv.level = invitee_level
    inv.save()
    return inv


def get_invitations_left(user):
    """
    Get user invitations left
    """
    num_inv = Invitations.objects.filter(source=user).count()
    return user.max_invitations - num_inv


def remove_invitation(invitation):
    """
    Removes an invitation and the invited user
    """
    if invitation is not None:
        if isinstance(invitation, Invitations):
            if invitation.target is not None:
                invitation.target.delete()
            invitation.delete()


class InvitationException(Exception):
    def __init__(self, msg):
        self.messages = [msg]


class TooManyInvitations(InvitationException):
    pass


class AlreadyInvited(InvitationException):
    pass
