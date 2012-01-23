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

from django.conf import settings
from django.utils.importlib import import_module
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from django.contrib.auth.forms import UserCreationForm
from django.contrib.sites.models import Site
from django.contrib import messages

from smtplib import SMTPException
from urllib import quote

from astakos.im.util import get_or_create_user
from astakos.im.models import AstakosUser, Invitation
from astakos.im.forms import ExtendedUserCreationForm, InvitedExtendedUserCreationForm

def get_backend():
    """
    Return an instance of a registration backend,
    according to the INVITATIONS_ENABLED setting
    (if True returns ``astakos.im.backends.InvitationsBackend`` and if False
    returns ``astakos.im.backends.SimpleBackend``).
    
    If the backend cannot be located ``django.core.exceptions.ImproperlyConfigured``
    is raised.
    """
    module = 'astakos.im.backends'
    prefix = 'Invitations' if settings.INVITATIONS_ENABLED else 'Simple'
    backend_class_name = '%sBackend' %prefix
    try:
        mod = import_module(module)
    except ImportError, e:
        raise ImproperlyConfigured('Error loading registration backend %s: "%s"' % (module, e))
    try:
        backend_class = getattr(mod, backend_class_name)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define a registration backend named "%s"' % (module, attr))
    return backend_class()

class InvitationsBackend(object):
    """
    A registration backend which implements the following workflow: a user
    supplies the necessary registation information, if the request contains a valid
    inivation code the user is automatically activated otherwise an inactive user
    account is created and the user is going to receive an email as soon as an
    administrator activates his/her account.
    """
    def get_signup_form(self, request):
        """
        Returns the necassary registration form depending the user is invited or not
        
        Throws Invitation.DoesNotExist in case ``code`` is not valid.
        """
        code = request.GET.get('code', '')
        formclass = 'ExtendedUserCreationForm'
        initial_data = None
        if request.method == 'GET':
            if code:
                formclass = 'Invited%s' %formclass
                self.invitation = Invitation.objects.get(code=code)
                if self.invitation.is_consumed:
                    raise Exception('Invitation has beeen used')
                initial_data = {'username':self.invitation.username,
                                'email':self.invitation.username,
                                'realname':self.invitation.realname}
                inviter = AstakosUser.objects.get(username=self.invitation.inviter)
                initial_data['inviter'] = inviter.realname
        else:
            initial_data = request.POST
        return globals()[formclass](initial_data)
    
    def _is_preaccepted(self, user):
        """
        If there is a valid, not-consumed invitation code for the specific user
        returns True else returns False.
        
        It should be called after ``get_signup_form`` which sets invitation if exists.
        """
        invitation = getattr(self, 'invitation') if hasattr(self, 'invitation') else None
        if not invitation:
            return False
        if invitation.username == user.username and not invitation.is_consumed:
            return True
        return False
    
    def signup(self, request):
        """
        Creates a incative user account. If the user is preaccepted (has a valid
        invitation code) the user is activated and if the request param ``next``
        is present redirects to it.
        In any other case the method returns the action status and a message.
        """
        kwargs = {}
        form = self.get_signup_form(request)
        user = form.save()
        
        try:
            if self._is_preaccepted(user):
                user.is_active = True
                user.save()
                message = _('Registration completed. You can now login.')
                next = request.POST.get('next')
                if next:
                    return redirect(next)
            else:
                message = _('Registration completed. You will receive an email upon your account\'s activation')
            status = messages.SUCCESS
        except Invitation.DoesNotExist, e:
            status = messages.ERROR
            message = _('Invalid invitation code')
        return status, message

class SimpleBackend(object):
    """
    A registration backend which implements the following workflow: a user
    supplies the necessary registation information, an incative user account is
    created and receives an email in order to activate his/her account.
    """
    def get_signup_form(self, request):
        """
        Returns the UserCreationForm
        """
        initial_data = request.POST if request.method == 'POST' else None
        return UserCreationForm(initial_data)
    
    def signup(self, request, email_template_name='activation_email.txt'):
        """
        Creates an inactive user account and sends a verification email.
        
        ** Arguments **
        
        ``email_template_name``
            A custom template for the verification email body to use. This is
            optional; if not specified, this will default to
            ``activation_email.txt``.
        
        ** Templates **
            activation_email.txt or ``email_template_name`` keyword argument
        
        ** Settings **
        
        * ACTIVATION_LOGIN_TARGET: Where users should activate their local account
        * DEFAULT_CONTACT_EMAIL: service support email
        * DEFAULT_FROM_EMAIL: from email
        """
        kwargs = {}
        form = self.get_signup_form(request)
        user = form.save()
        
        status = messages.SUCCESS
        try:
            _send_verification(request, user, email_template_name)
            message = _('Verification sent to %s' % user.email)
        except (SMTPException, socket.error) as e:
            status = messages.ERROR
            name = 'strerror'
            message = getattr(e, name) if hasattr(e, name) else e
        return status, message

    def _send_verification(request, user, template_name):
        site = Site.objects.get_current()
        baseurl = request.build_absolute_uri('/').rstrip('/')
        url = settings.ACTIVATION_LOGIN_TARGET % (baseurl,
                                                  quote(user.auth_token),
                                                  quote(baseurl))
        message = render_to_string(template_name, {
                'user': user,
                'url': url,
                'baseurl': baseurl,
                'site_name': site.name,
                'support': settings.DEFAULT_CONTACT_EMAIL})
        sender = settings.DEFAULT_FROM_EMAIL
        send_mail('Pithos account activation', message, sender, [user.email])
        logging.info('Sent activation %s', user)
