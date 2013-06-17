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

from django.conf.urls.defaults import patterns, url

from astakos.im.forms import (
    ExtendedPasswordResetForm,
    ExtendedPasswordChangeForm,
    ExtendedSetPasswordForm, LoginForm)

from astakos.im import settings

urlpatterns = patterns(
    'astakos.im.views',
    url(r'^$', 'index', {}, name='index'),
    url(r'^login/?$', 'login', {}, name='login'),
    url(r'^landing/?$', 'landing', {}, name='landing'),
    url(r'^profile/update_token?$', 'update_token', {}, name='update_token'),
    url(r'^profile/?$', 'edit_profile', {}, name='edit_profile'),
    url(r'^api_access/?$', 'api_access', {}, name='api_access'),
    url(r'^\.kamakirc/?$', 'api_access_config', {}, name='api_access_config'),
    url(r'^feedback/?$', 'feedback', {}, name='feedback'),
    url(r'^signup/?$', 'signup',
        {
            'on_success': 'index',
            'extra_context': {'login_form': LoginForm()}}, name='signup'),
    url(r'^logout/?$', 'logout',
        {
            'template': 'im/login.html',
            'extra_context': {'login_form': LoginForm()}}, name='logout'),
    url(r'^activate/?$', 'activate', {}, name='activate'),
    url(r'^approval_terms/?$', 'approval_terms', {}, name='latest_terms'),
    url(r'^approval_terms/(?P<term_id>\d+)/?$', 'approval_terms'),
    url(r'^send/activation/(?P<user_id>\d+)/?$', 'send_activation', {},
        name='send_activation'),
    url(r'^resources/?$', 'resource_usage', {}, name='resource_usage'),

#    url(r'^billing/?$', 'billing', {}, name='billing'),
#    url(r'^timeline/?$', 'timeline', {}, name='timeline'),

    url(r'^projects/add/?$', 'project_add', {}, name='project_add'),
    url(r'^projects/?$', 'project_list', {}, name='project_list'),
    url(r'^projects/search/?$', 'project_search', {}, name='project_search'),
    url(r'^projects/(?P<chain_id>\d+)/?$', 'project_detail', {},
        name='project_detail'),
    url(r'^projects/(?P<chain_id>\d+)/join/?$', 'project_join', {},
        name='project_join'),
    url(r'^projects/(?P<chain_id>\d+)/leave/?$', 'project_leave', {},
        name='project_leave'),
    url(r'^projects/(?P<chain_id>\d+)/cancel/?$', 'project_cancel', {},
        name='project_cancel'),
    url(r'^projects/(?P<chain_id>\d+)/members/?$', 'project_members', {},
        name='project_members'),
    url(r'^projects/(?P<chain_id>\d+)/members/approved/?$', 'project_members',
        {'members_status_filter': 1}, name='project_approved_members'),
    url(r'^projects/(?P<chain_id>\d+)/members/accept/?$',
        'project_members_action', {'action': 'accept'},
        name='project_members_accept'),
    url(r'^projects/(?P<chain_id>\d+)/members/remove/?$',
        'project_members_action', {'action': 'remove'},
        name='project_members_remove'),
    url(r'^projects/(?P<chain_id>\d+)/members/reject/?$',
        'project_members_action', {'action': 'reject'},
        name='project_members_reject'),
    url(r'^projects/(?P<chain_id>\d+)/members/pending/?$', 'project_members',
        {'members_status_filter': 0}, name='project_pending_members'),
    url(r'^projects/(?P<chain_id>\d+)/(?P<memb_id>\d+)/accept/?$',
        'project_accept_member', {}, name='project_accept_member'),
    url(r'^projects/(?P<chain_id>\d+)/(?P<memb_id>\d+)/reject/?$',
        'project_reject_member', {}, name='project_reject_member'),
    url(r'^projects/(?P<chain_id>\d+)/(?P<memb_id>\d+)/remove/?$',
        'project_remove_member', {}, name='project_remove_member'),
    url(r'^projects/app/(?P<application_id>\d+)/?$', 'project_app', {},
        name='project_app'),
    url(r'^projects/app/(?P<application_id>\d+)/modify$', 'project_modify', {},
        name='project_modify'),
    url(r'^projects/app/(?P<application_id>\d+)/approve$',
        'project_app_approve', {}, name='project_app_approve'),
    url(r'^projects/app/(?P<application_id>\d+)/deny$', 'project_app_deny', {},
        name='project_app_deny'),
    url(r'^projects/app/(?P<application_id>\d+)/dismiss$',
        'project_app_dismiss', {}, name='project_app_dismiss'),
    url(r'^projects/app/(?P<application_id>\d+)/cancel$', 'project_app_cancel',
        {}, name='project_app_cancel'),

    url(r'^projects/how_it_works/?$', 'how_it_works', {}, name='how_it_works'),
    url(r'^remove_auth_provider/(?P<pk>\d+)?$', 'remove_auth_provider', {},
        name='remove_auth_provider'),
)


if settings.EMAILCHANGE_ENABLED:
    urlpatterns += patterns(
        'astakos.im.views',
        url(r'^email_change/?$', 'change_email', {}, name='email_change'),
        url(r'^email_change/confirm/(?P<activation_key>\w+)/?$',
            'change_email', {},
            name='email_change_confirm'))

if 'local' in settings.IM_MODULES:
    urlpatterns += patterns(
        'astakos.im.views.target.local',
        url(r'^local/?$', 'login', name='local_login'),
        url(r'^password_change/?$', 'password_change', {
            'post_change_redirect': 'profile',
            'password_change_form': ExtendedPasswordChangeForm},
            name='password_change'),
        url(r'^local/password_reset/done$', 'password_reset_done'),
        url(r'^local/reset/confirm/done$',
            'password_reset_confirm_done'),
        url(r'^local/password_reset/?$', 'password_reset', {
            'email_template_name': 'registration/password_email.txt',
            'password_reset_form': ExtendedPasswordResetForm,
            'post_reset_redirect': 'password_reset/done'}),
        url(r'^local/password_reset_done/?$', 'password_reset_done'),
        url(r'^local/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/?$',
            'password_reset_confirm', {
                'set_password_form': ExtendedSetPasswordForm,
                'post_reset_redirect': 'done'}),
        url(r'^local/password/reset/complete/?$', 'password_reset_complete')
    )

if settings.INVITATIONS_ENABLED:
    urlpatterns += patterns(
        'astakos.im.views',
        url(r'^invite/?$', 'invite', {}, name='invite'))

if 'shibboleth' in settings.IM_MODULES:
    urlpatterns += patterns(
        'astakos.im.views.target',
        url(r'^login/shibboleth/?$', 'shibboleth.login'),
    )

if 'twitter' in settings.IM_MODULES:
    urlpatterns += patterns(
        'astakos.im.views.target',
        url(r'^login/twitter/?$', 'twitter.login'),
        url(r'^login/twitter/authenticated/?$',
            'twitter.authenticated'))

if 'google' in settings.IM_MODULES:
    urlpatterns += patterns(
        'astakos.im.views.target',
        url(r'^login/google/?$', 'google.login'),
        url(r'^login/google/authenticated/?$',
            'google.authenticated'))

if 'linkedin' in settings.IM_MODULES:
    urlpatterns += patterns(
        'astakos.im.views.target',
        url(r'^login/linkedin/?$', 'linkedin.login'),
        url(r'^login/linkedin/authenticated/?$',
            'linkedin.authenticated'))

urlpatterns += patterns(
    'astakos.im.views',
    url(r'^get_menu/?$', 'get_menu'),
    url(r'^get_services/?$', 'get_services'))

urlpatterns += patterns(
    'astakos.api.user',
    url(r'^authenticate/?$', 'authenticate'))
