from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.core.validators import validate_email

from synnefo.api.common import method_not_allowed
from synnefo.db.models import Invitations, SynnefoUser
from synnefo.logic import users

import json

def send_emails(request):
    errors = ()
    valid_inv = filter(lambda x: x.startswith("name_"), request.POST.keys())

    for inv in valid_inv:
        (name, inv_id) = inv.split('_')

        try:
            email = request.POST['email_' + inv_id]
            name = request.POST[inv]

            validate_email(email)
            validate_name(name)
            add_invitation(request.user, name, email)
        except Exception as e:
            errors += e.message
        except ValidationError as v:
            errors += v.message

    response = HttpResponseRedirect("/invitations/")
    return response

def validate_name(name):
    if name is None or name.strip() == '' :
        raise ValidationError("Name cannot be empty")

    return True

def invitations_for_user(request):
    invitations = []

    for inv in Invitations.objects.filter(source = request.user):
        invitations.append(invitation_to_dict(inv))

    return invitations

def invitation_to_dict(inv):
    invitation = {}

    invitation['sourcename'] = inv.source.realname
    invitation['source'] = inv.source.uniq
    invitation['targetname'] = inv.target.realname
    invitation['target'] = inv.target.uniq
    invitation['accepted'] = inv.accepted
    invitation['sent'] = inv.created

    return invitation

def inv_demux(request):
    if request.method == 'GET':
        data = render_to_string('invitations.html',
                                {'invitations': invitations_for_user(request)})
        return  HttpResponse(data)
    elif request.method == 'POST':
        return send_emails(request)
    else:
        method_not_allowed(request)

@transaction.commit_on_success
def add_invitation(source, name, email):
    """
        Adds an invitation, if the source user has not gone over his/her
        invitation count or the target user has not been invited already
    """
    num_inv = Invitations.objects.filter(source = source).count()

    if num_inv >= settings.MAX_INVITATIONS:
        raise TooManyInvitations(source)

    target = SynnefoUser.objects.filter(name = name, uniq = email)

    if target.count() is not 0:
        raise AlreadyInvited("User already invited: %s <%s>" % (name, email))

    users.register_user(name, email)

    target = SynnefoUser.objects.filter(uniq = email)

    r = list(target[:1])
    if not r:
        raise Exception

    inv = Invitations()
    inv.source = source
    inv.target = target[0]
    inv.save()

@transaction.commit_on_success
def invitation_accepted(invitation):
    """
        Mark an invitation as accepted
    """
    invitation.accepted = True
    invitation.save()

class TooManyInvitations(BaseException):

    def __init__(self, source):
        self.source = source


class AlreadyInvited(BaseException):

    def __init__(self, msg):
        self.msg = msg
