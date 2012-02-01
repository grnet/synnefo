# Copyright 2011-2012 GRNET S.A. All rights reserved.
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
from django.conf.urls.defaults import patterns, include, url
from django.core.urlresolvers import reverse

from astakos.im.forms import ExtendedPasswordResetForm

urlpatterns = patterns('astakos.im.views',
    url(r'^$', 'index'),
    url(r'^login/?$', 'index'),
    url(r'^profile/?$', 'edit_profile'),
    url(r'^feedback/?$', 'send_feedback'),
    url(r'^signup/?$', 'signup'),
    url(r'^user_logout/?$', 'user_logout'),
    url(r'^admin/', include('astakos.im.admin.urls')),
)

urlpatterns += patterns('django.contrib.auth.views',
    url(r'^logout/?$', 'logout')
)

urlpatterns += patterns('astakos.im.target',
    url(r'^login/redirect/?$', 'redirect.login')
)

urlpatterns += patterns('',
    url(r'^static/(?P<path>.*)$', 'django.views.static.serve',
                                {'document_root': settings.PROJECT_PATH + '/im/static'})
)

if 'local' in settings.IM_MODULES:
    urlpatterns += patterns('astakos.im.target',
        url(r'^local/?$', 'local.login'),
        url(r'^local/activate/?$', 'local.activate'),
    )
    urlpatterns += patterns('django.contrib.auth.views',
        url(r'^local/password_reset/?$', 'password_reset',
         {'email_template_name':'registration/password_email.txt',
          'password_reset_form':ExtendedPasswordResetForm}),
        url(r'^local/password_reset_done/?$', 'password_reset_done'),
        url(r'^local/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
         'password_reset_confirm'),
        url(r'^local/password/reset/complete/$', 'password_reset_complete'),
        url(r'^password/?$', 'password_change', {'post_change_redirect':'profile'})
    )

if settings.INVITATIONS_ENABLED:
    urlpatterns += patterns('astakos.im.views',
        url(r'^invite/?$', 'invite'),
    )
    urlpatterns += patterns('astakos.im.target',
        url(r'^login/invitation/?$', 'invitation.login')
    )

if 'shibboleth' in settings.IM_MODULES:
    urlpatterns += patterns('astakos.im.target',
        url(r'^login/shibboleth/?$', 'shibboleth.login')
    )

if 'twitter' in settings.IM_MODULES:
    urlpatterns += patterns('astakos.im.target',
        url(r'^login/twitter/?$', 'twitter.login'),
        url(r'^login/twitter/authenticated/?$', 'twitter.authenticated')
    )

urlpatterns += patterns('astakos.im.api',
    url(r'^authenticate/?$', 'authenticate')
)
    
