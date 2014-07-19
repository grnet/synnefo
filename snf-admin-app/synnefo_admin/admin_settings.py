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


"""
Settings for the snf-admin-app.
"""

# --------------------------------------------------------------------
# Process Admin settings

from django.conf import settings

ADMIN_ENABLED = getattr(settings, 'ADMIN_ENABLED', True)

ADMIN_MEDIA_URL = getattr(settings, 'ADMIN_MEDIA_URL',
                          settings.MEDIA_URL + 'admin/')

AUTH_COOKIE_NAME = getattr(settings, 'ADMIN_AUTH_COOKIE_NAME',
                           getattr(settings, 'UI_AUTH_COOKIE_NAME',
                                   '_pithos2_a'))

# Check if the user has defined his/her own values for the following three
# groups.
ADMIN_READONLY_GROUP = getattr(settings, 'ADMIN_READONLY_GROUP',
                               'admin-readonly')
ADMIN_HELPDESK_GROUP = getattr(settings, 'ADMIN_HELPDESK_GROUP', 'helpdesk')
ADMIN_GROUP = getattr(settings, 'ADMIN_GROUP', 'admin')

# The user can either use the above three groups to control who has access
# to the admin tool, or define its own.
DEFAULT_ADMIN_PERMITTED_GROUPS = [ADMIN_READONLY_GROUP, ADMIN_HELPDESK_GROUP,
                                  ADMIN_GROUP]
ADMIN_PERMITTED_GROUPS = getattr(settings, 'ADMIN_PERMITTED_GROUPS',
                                 DEFAULT_ADMIN_PERMITTED_GROUPS)

# The user can either use our RBAC definition, which uses the above 3 groups
# (readonly, helpdesk, admin), or define its own.
DEFAULT_ADMIN_RBAC = {
    'user': {
        'activate': [ADMIN_GROUP],
        'deactivate': [ADMIN_GROUP],
        'accept': [ADMIN_GROUP],
        'reject': [ADMIN_GROUP],
        'verify': [ADMIN_GROUP],
        'resend_verification': [ADMIN_GROUP],
        'contact': [ADMIN_HELPDESK_GROUP, ADMIN_GROUP],
    }, 'vm': {
        'start': [ADMIN_HELPDESK_GROUP, ADMIN_GROUP],
        'shutdown': [ADMIN_HELPDESK_GROUP, ADMIN_GROUP],
        'reboot': [ADMIN_HELPDESK_GROUP, ADMIN_GROUP],
        'destroy': [ADMIN_GROUP],
        'suspend': [ADMIN_HELPDESK_GROUP, ADMIN_GROUP],
        'unsuspend': [ADMIN_HELPDESK_GROUP, ADMIN_GROUP],
        'contact': [ADMIN_HELPDESK_GROUP, ADMIN_GROUP],
    }, 'volume': {
        'contact': [ADMIN_HELPDESK_GROUP, ADMIN_GROUP],
    }, 'network': {
        'drain': [ADMIN_GROUP],
        'undrain': [ADMIN_GROUP],
        'destroy': [ADMIN_GROUP],
        'contact': [ADMIN_HELPDESK_GROUP, ADMIN_GROUP],
    }, 'ip': {
        'destroy': [ADMIN_GROUP],
        'contact': [ADMIN_HELPDESK_GROUP, ADMIN_GROUP],
    }, 'project': {
        'approve': [ADMIN_GROUP],
        'deny': [ADMIN_GROUP],
        'suspend': [ADMIN_GROUP],
        'unsuspend': [ADMIN_GROUP],
        'terminate': [ADMIN_GROUP],
        'reinstate': [ADMIN_GROUP],
        'contact': [ADMIN_GROUP],
    },
}
ADMIN_RBAC = getattr(settings, 'ADMIN_RBAC', DEFAULT_ADMIN_RBAC)

# With this option, the user can define whether to show deleted items on the
# details page of another item. Note that the details page of the deleted
# item will be shown properly.
ADMIN_SHOW_DELETED_ASSOCIATED_ITEMS = getattr(
    settings, 'ADMIN_SHOW_DELETED_ASSOCIATED_ITEMS', False)

# With this option, the user can define the number of associated items that
# will be shown for each category, so as not to flood the page.
ADMIN_LIMIT_ASSOCIATED_ITEMS_PER_CATEGORY = getattr(
    settings, 'ADMIN_LIMIT_ASSOCIATED_ITEMS_PER_CATEGORY', 50)
