# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls import patterns, url
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

    # url(r'^billing/?$', 'billing', {}, name='billing'),
    # url(r'^timeline/?$', 'timeline', {}, name='timeline'),

    # projects urls
    url(r'^projects/?$',
        'project_list', {}, name='project_list'),
    url(r'^projects/add/?$',
        'project_add_or_modify', {}, name='project_add'),
    url(r'^projects/search/?$',
        'project_search', {}, name='project_search'),
    url(r'^projects/(?P<project_uuid>[^/]+)/?$',
        'project_or_app_detail', {}, name='project_detail'),

    # user project actions
    url(r'^projects/(?P<project_uuid>[^/]+)/join/?$',
        'project_join', name='project_join'),
    url(r'^projects/(?P<project_uuid>[^/]+)/leave/?$',
        'project_leave', name='project_leave'),
    url(r'^projects/(?P<project_uuid>[^/]+)/cancel-join-request/?$',
        'project_cancel_join', name='project_cancel_join'),

    # project members urls
    url(r'^projects/(?P<project_uuid>[^/]+)/members/?$',
        'project_members', {}, name='project_members'),
    url(r'^projects/(?P<project_uuid>[^/]+)/members/approved/?$',
        'project_members', {'members_status_filter': 1},
        name='project_approved_members'),
    url(r'^projects/(?P<project_uuid>[^/]+)/members/pending/?$',
        'project_members', {'members_status_filter': 0},
        name='project_pending_members'),

    # project admin members actions (batch/single)
    url(r'^projects/(?P<project_uuid>[^/]+)/members/accept/?$',
        'project_members_action', {'action': 'accept'},
        name='project_members_accept'),
    url(r'^projects/(?P<project_uuid>[^/]+)/members/remove/?$',
        'project_members_action', {'action': 'remove'},
        name='project_members_remove'),
    url(r'^projects/(?P<project_uuid>[^/]+)/members/reject/?$',
        'project_members_action', {'action': 'reject'},
        name='project_members_reject'),
    url(r'^projects/(?P<project_uuid>[^/]+)/memberships/(?P<memb_id>\d+)/accept/?$',
        'project_members_action', {'action': 'accept'},
        name='project_accept_member'),
    url(r'^projects/(?P<project_uuid>[^/]+)/memberships/(?P<memb_id>\d+)/reject/?$',
        'project_members_action', {'action': 'reject'},
        name='project_reject_member'),
    url(r'^projects/(?P<project_uuid>[^/]+)/memberships/(?P<memb_id>\d+)/remove/?$',
        'project_members_action', {'action': 'remove'},
        name='project_remove_member'),

    # project application urls
    url(r'^projects/(?P<project_uuid>[^/]+)/app/(?P<app_id>\d+)/?$',
        'project_or_app_detail', {}, name='project_app'),
    url(r'^projects/(?P<project_uuid>[^/]+)/modify$', 'project_add_or_modify',
        {}, name='project_modify'),
    url(r'^projects/(?P<project_uuid>[^/]+)/app/(?P<application_id>\d+)/approve?$',
        'project_app_approve', {}, name='project_app_approve'),
    url(r'^projects/(?P<project_uuid>[^/]+)/app/(?P<application_id>\d+)/deny?$',
        'project_app_deny', {}, name='project_app_deny'),
    url(r'^projects/(?P<project_uuid>[^/]+)/app/(?P<application_id>\d+)/dismiss?$',
        'project_app_dismiss', {}, name='project_app_dismiss'),
    url(r'^projects/(?P<project_uuid>[^/]+)/app/(?P<application_id>\d+)/cancel?$',
        'project_app_cancel', {}, name='project_app_cancel'),

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
        url(r'^login/local/?$', 'login', name='local_login'),
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
