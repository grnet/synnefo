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

from astakos.im.settings import IM_MODULES, INVITATIONS_ENABLED, IM_STATIC_URL, \
        COOKIE_NAME
from django.conf import settings
from django.core.urlresolvers import reverse

def im_modules(request):
    return {'im_modules': IM_MODULES}

def next(request):
    return {'next' : request.GET.get('next', '')}

def code(request):
    return {'code' : request.GET.get('code', '')}

def invitations(request):
    return {'invitations_enabled' :INVITATIONS_ENABLED}

def media(request):
    return {'IM_STATIC_URL' : IM_STATIC_URL}

def cloudbar(request):
    """
    Cloudbar configuration
    """
    CB_LOCATION = getattr(settings, 'CLOUDBAR_LOCATION', IM_STATIC_URL + 'cloudbar/')
    CB_COOKIE_NAME = getattr(settings, 'CLOUDBAR_COOKIE_NAME', COOKIE_NAME)
    CB_ACTIVE_SERVICE = getattr(settings, 'CLOUDBAR_ACTIVE_SERVICE', 'cloud')
    
    absolute = lambda (url): request.build_absolute_uri(url)
    
    return {'CLOUDBAR_LOC': CB_LOCATION,
            'CLOUDBAR_COOKIE_NAME': CB_COOKIE_NAME,
            'ACTIVE_SERVICE': CB_ACTIVE_SERVICE,
            'GET_SERVICES_URL': absolute(reverse('astakos.im.api.get_services')),
            'GET_MENU_URL': absolute(reverse('astakos.im.api.get_menu'))}
