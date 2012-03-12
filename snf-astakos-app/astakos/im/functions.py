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

import logging

from django.utils.translation import ugettext as _
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from urlparse import urljoin
from random import randint

from astakos.im.settings import DEFAULT_CONTACT_EMAIL, DEFAULT_FROM_EMAIL, SITENAME, BASEURL
from astakos.im.models import Invitation, AstakosUser

logger = logging.getLogger(__name__)

def activate(user, email_template_name='im/welcome_email.txt'):
    """
    Activates the specific user and sends email.
    
    Raises SMTPException, socket.error
    """
    user.is_active = True
    user.save()
    subject = _('Welcome to %s' % SITENAME)
    message = render_to_string(email_template_name, {
                'user': user,
                'url': urljoin(BASEURL, reverse('astakos.im.views.index')),
                'baseurl': BASEURL,
                'site_name': SITENAME,
                'support': DEFAULT_CONTACT_EMAIL})
    sender = DEFAULT_FROM_EMAIL
    send_mail(subject, message, sender, [user.email])
    logger.info('Sent greeting %s', user)

def _generate_invitation_code():
    while True:
        code = randint(1, 2L**63 - 1)
        try:
            Invitation.objects.get(code=code)
            # An invitation with this code already exists, try again
        except Invitation.DoesNotExist:
            return code

def invite(inviter, username, realname):
    """
    Send an invitation email and upon success reduces inviter's invitation by one.
    
    Raises SMTPException, socket.error
    """
    code = _generate_invitation_code()
    invitation = Invitation(inviter=inviter,
                            username=username,
                            code=code,
                            realname=realname)
    invitation.save()
    subject = _('Invitation to %s' % SITENAME)
    url = '%s?code=%d' % (urljoin(BASEURL, reverse('astakos.im.views.signup')), code)
    message = render_to_string('im/invitation.txt', {
                'invitation': invitation,
                'url': url,
                'baseurl': BASEURL,
                'service': SITENAME,
                'support': DEFAULT_CONTACT_EMAIL})
    sender = DEFAULT_FROM_EMAIL
    send_mail(subject, message, sender, [invitation.username])
    logger.info('Sent invitation %s', invitation)
    inviter.invitations = max(0, inviter.invitations - 1)
    inviter.save()

def set_user_credibility(email, has_credits):
    try:
        user = AstakosUser.objects.get(email=email)
        user.has_credits = has_credits
        user.save()
    except AstakosUser.DoesNotExist, e:
        logger.exception(e)