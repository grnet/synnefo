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
from django.conf.urls.defaults import patterns, include
from django.core.urlresolvers import reverse

urlpatterns = patterns('astakos.im.views',
    (r'^$', 'index'),
    (r'^login/?$', 'index'),
    (r'^profile/?$', 'edit_profile'),
    (r'^feedback/?$', 'send_feedback'),
    (r'^signup/?$', 'signup'),
    (r'^admin/', include('astakos.im.admin.urls')),
)

urlpatterns += patterns('django.contrib.auth.views',
    (r'^logout/?$', 'logout'),
    (r'^password/?$', 'password_change', {'post_change_redirect':'admin'}),
)

urlpatterns += patterns('astakos.im.target',
    (r'^login/dummy/?$', 'dummy.login')
)

urlpatterns += patterns('',
    (r'^static/(?P<path>.*)$', 'django.views.static.serve',
                                {'document_root': settings.PROJECT_PATH + '/im/static'})
)

if 'local' in settings.IM_MODULES:
    urlpatterns += patterns('astakos.im.target',
        (r'^local/?$', 'local.login'),
        (r'^local/activate/?$', 'local.activate'),
    )
    urlpatterns += patterns('django.contrib.auth.views',
        (r'^local/password_reset/?$', 'password_reset',
         {'email_template_name':'registration/password_email.txt'}),
        (r'^local/password_reset_done/?$', 'password_reset_done'),
        (r'^local/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
         'password_reset_confirm'),
        (r'^local/password/reset/complete/$', 'password_reset_complete')
    )

if settings.INVITATIONS_ENABLED:
    urlpatterns += patterns('astakos.im.views',
        (r'^invite/?$', 'invite'),
    )
    urlpatterns += patterns('astakos.im.target',
        (r'^login/invitation/?$', 'invitation.login')
    )

if 'shibboleth' in settings.IM_MODULES:
    urlpatterns += patterns('astakos.im.target',
        (r'^login/shibboleth/?$', 'shibboleth.login')
    )

if 'twitter' in settings.IM_MODULES:
    urlpatterns += patterns('astakos.im.target',
        (r'^login/twitter/?$', 'twitter.login'),
        (r'^login/twitter/authenticated/?$', 'twitter.authenticated')
    )

urlpatterns += patterns('astakos.im.api',
    (r'^authenticate/?$', 'authenticate')
)
    
