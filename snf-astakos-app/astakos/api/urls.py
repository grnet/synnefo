# Copyright 2013 GRNET S.A. All rights reserved.
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

from django.conf.urls import patterns, url, include
from snf_django.lib.api import api_endpoint_not_found


astakos_account_v1_0 = patterns(
    'astakos.api.quotas',
    url(r'^quotas/?$', 'quotas', name="astakos-api-quotas"),
    url(r'^service_quotas/?$', 'service_quotas'),
    url(r'^resources/?$', 'resources'),
    url(r'^commissions/?$', 'commissions'),
    url(r'^commissions/action/?$', 'resolve_pending_commissions'),
    url(r'^commissions/(?P<serial>\d+)/?$', 'get_commission'),
    url(r'^commissions/(?P<serial>\d+)/action/?$', 'serial_action'),
)

astakos_account_v1_0 += patterns(
    'astakos.api.user',
    url(r'^feedback/?$', 'send_feedback'),
    url(r'^user_catalogs/?$', 'get_uuid_displayname_catalogs'),
)

astakos_account_v1_0 += patterns(
    'astakos.api.service',
    url(r'^service/user_catalogs/?$', 'get_uuid_displayname_catalogs'),
)

astakos_account_v1_0 += patterns(
    'astakos.api.projects',
    url(r'^projects/?$', 'projects', name='api_projects'),
    url(r'^projects/(?P<project_id>\d+)/?$', 'project', name='api_project'),
    url(r'^projects/(?P<project_id>\d+)/action/?$', 'project_action',
        name='api_project_action'),
    url(r'^projects/apps/?$', 'applications', name='api_applications'),
    url(r'^projects/apps/(?P<app_id>\d+)/?$', 'application',
        name='api_application'),
    url(r'^projects/apps/(?P<app_id>\d+)/action/?$', 'application_action',
        name='api_application_action'),
    url(r'^projects/memberships/?$', 'memberships', name='api_memberships'),
    url(r'^projects/memberships/(?P<memb_id>\d+)/?$', 'membership',
        name='api_membership'),
    url(r'^projects/memberships/(?P<memb_id>\d+)/action/?$',
        'membership_action', name='api_membership_action'),
)

urlpatterns = patterns(
    '',
    url(r'^v1.0/', include(astakos_account_v1_0)),
    (r'^.*', api_endpoint_not_found),
)
