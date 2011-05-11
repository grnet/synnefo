from django import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import Template
from synnefo.api.common import method_not_allowed

from synnefo.db.models import SynnefoUser

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
        t = Template()
        data = t.render('invitation.html', {'invitations': None})
        return  HttpResponse(data)
    elif request.method == 'POST':
        f = InvitationForm(request)
    else:
        method_not_allowed(request)