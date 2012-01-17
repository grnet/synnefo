# Copyright 2011 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.
import socket
import logging

from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from smtplib import SMTPException
from urllib import quote

from astakos.im.forms import LocalRegisterForm
from astakos.im.util import get_or_create_user
from astakos.im.models import AstakosUser

class Backend(object):
    def get_signup_form(self, request):
        initial_data = request.POST if request.method == 'POST' else None
        return LocalRegisterForm(initial_data)
    
    def signup(self, request, form, success_url):
        kwargs = {}
        for field in form.fields:
            if hasattr(AstakosUser(), field):
                kwargs[field] = form.cleaned_data[field]
        user = get_or_create_user(**kwargs)
        
        status = 'success'
        try:
            send_verification(request.build_absolute_uri('/').rstrip('/'), user)
            message = _('Verification sent to %s' % user.email)
        except (SMTPException, socket.error) as e:
            status = 'error'
            name = 'strerror'
            message = getattr(e, name) if hasattr(e, name) else e
        
        if user and status == 'error':
            #delete created user
            user.delete()
        return status, message

def send_verification(baseurl, user):
    url = settings.ACTIVATION_LOGIN_TARGET % (baseurl,
                                              quote(user.auth_token),
                                              quote(baseurl))
    message = render_to_string('activation.txt', {
            'user': user,
            'url': url,
            'baseurl': baseurl,
            'service': settings.SERVICE_NAME,
            'support': settings.DEFAULT_CONTACT_EMAIL})
    sender = settings.DEFAULT_FROM_EMAIL
    send_mail('Pithos account activation', message, sender, [user.email])
    logging.info('Sent activation %s', user)