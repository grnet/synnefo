from django import forms
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.loader import render_to_string
from synnefo.api.common import method_not_allowed
from synnefo.db.models import Invitations, SynnefoUser
from synnefo.logic import users

class InvitationForm(forms.Form):
    emails = forms.Textarea

    def send_emails(self, request):
        if request.method == 'POST': # If the form has been submitted...
            form = InvitationForm(request.POST) # A form bound to the POST data
            if form.is_valid(): # All validation rules pass
                # Process the data in form.cleaned_data
                # ...
                return HttpResponseRedirect('/thanks/') # Redirect after POST
        else:
            form = InvitationForm() # An unbound form

        return render_to_response('invitation.html', {'form': form,})

def inv_demux(request):
    if request.method == 'GET':
        invitations = Invitations.objects.filter(source = request.user)
        data = render_to_string('invitations.html', {'invitations': invitations})
        return  HttpResponse(data)
    elif request.method == 'POST':
        f = InvitationForm(request)
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