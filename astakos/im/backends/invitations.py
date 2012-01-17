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

from astakos.im.forms import InvitedLocalRegisterForm, LocalRegisterForm
from astakos.im.models import AstakosUser, Invitation

class Backend(object):
    def get_signup_form(self, request):
        code = request.GET.get('code', '')
        formclass = 'LocalRegisterForm'
        if request.method == 'GET':
            initial_data = None
            if code:
                formclass = 'InvitedLocalRegiterForm'
                invitation = Invitation.objects.get(code=code)
                if invitation.is_consumed:
                    return HttpResponseBadRequest('Invitation has beeen used')
                initial_data.update({'username':invitation.username,
                                       'email':invitation.username,
                                       'realname':invitation.realname})
                inviter = AstakosUser.objects.get(username=invitation.inviter)
                initial_data['inviter'] = inviter.realname
        else:
            initial_data = request.POST
        return globals()[formclass](initial_data)
    
    def is_preaccepted(user, code):
        invitation = self.invitation
        if invitation and not invitation.is_consumed and invitation.code == code:
            return True
        return False
    
    def signup(self, request, form):
        kwargs = {}
        for field in form.fields:
            if hasattr(AstakosUser(), field):
                kwargs[field] = form.cleaned_data[field]
        user = get_or_create_user(**kwargs)
        
        code = request.POST.get('code')
        if is_preaccepted(user, code):
            user.is_active = True
            user.save()
            message = _('Registration completed. You can now login.')
            next = request.POST.get('next')
            if next:
                return redirect(next)
        else:
            message = _('Registration completed. You will receive an email upon your account\'s activation')
        status = 'success'
        return status, message