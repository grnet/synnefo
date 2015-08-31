# Copyright (C) 2010-2015 GRNET S.A. and individual contributors
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
#

import os

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.template import loader
from django.http import HttpResponse
from django.utils.translation import get_language
from django.utils import simplejson as json
from synnefo_branding.utils import render_to_string
from django.core.urlresolvers import reverse
from django.template import RequestContext

from synnefo.util.version import get_component_version

from synnefo.ui import settings as uisettings

SYNNEFO_JS_LIB_VERSION = get_component_version('app')

# UI preferences settings
TIMEOUT = getattr(settings, "TIMEOUT", 10000)
UPDATE_INTERVAL = getattr(settings, "UI_UPDATE_INTERVAL", 5000)
CHANGES_SINCE_ALIGNMENT = getattr(settings, "UI_CHANGES_SINCE_ALIGNMENT", 0)
UPDATE_INTERVAL_INCREASE = getattr(settings, "UI_UPDATE_INTERVAL_INCREASE",
                                   500)
UPDATE_INTERVAL_INCREASE_AFTER_CALLS_COUNT = \
    getattr(settings, "UI_UPDATE_INTERVAL_INCREASE_AFTER_CALLS_COUNT", 3)
UPDATE_INTERVAL_FAST = getattr(settings, "UI_UPDATE_INTERVAL_FAST", 2500)
UPDATE_INTERVAL_MAX = getattr(settings, "UI_UPDATE_INTERVAL_MAX", 10000)

# predefined values settings
VM_IMAGE_COMMON_METADATA = \
    getattr(settings, "UI_VM_IMAGE_COMMON_METADATA", ["OS", "users"])
SUGGESTED_FLAVORS_DEFAULT = {}
SUGGESTED_FLAVORS = getattr(settings, "VM_CREATE_SUGGESTED_FLAVORS",
                            SUGGESTED_FLAVORS_DEFAULT)
SUGGESTED_ROLES_DEFAULT = ["Database server", "File server", "Mail server",
                           "Web server", "Proxy"]
SUGGESTED_ROLES = getattr(settings, "VM_CREATE_SUGGESTED_ROLES",
                          SUGGESTED_ROLES_DEFAULT)
IMAGE_ICONS = settings.IMAGE_ICONS
IMAGE_DELETED_TITLE = \
    getattr(settings, 'UI_IMAGE_DELETED_TITLE', '(deleted)')
IMAGE_DELETED_SIZE_TITLE = \
    getattr(settings, 'UI_IMAGE_DELETED_SIZE_TITLE', '(none)')


SSH_SUPPORT_OSFAMILY_EXCLUDE_LIST = getattr(
    settings, "UI_SSH_SUPPORT_OSFAMILY_EXCLUDE_LIST", ['windows'])

OS_CREATED_USERS = getattr(settings, "UI_OS_DEFAULT_USER_MAP")
UNKNOWN_OS = getattr(settings, "UI_UNKNOWN_OS", "unknown")

AUTH_COOKIE_NAME = getattr(settings, "UI_AUTH_COOKIE_NAME", 'synnefo_user')

# never change window location. Helpful in development environments
AUTH_SKIP_REDIRECTS = getattr(settings, "UI_AUTH_SKIP_REDIRECTS", False)

# UI behaviour settings
DELAY_ON_BLUR = getattr(settings, "UI_DELAY_ON_BLUR", True)
UPDATE_HIDDEN_VIEWS = getattr(settings, "UI_UPDATE_HIDDEN_VIEWS", False)
HANDLE_WINDOW_EXCEPTIONS = \
    getattr(settings, "UI_HANDLE_WINDOW_EXCEPTIONS", True)
SKIP_TIMEOUTS = getattr(settings, "UI_SKIP_TIMEOUTS", 1)

# Additional settings
VM_NAME_TEMPLATE = getattr(settings, "VM_CREATE_NAME_TPL", "My {0} server")
NO_FQDN_MESSAGE = getattr(settings, "UI_NO_FQDN_MESSAGE", "No available FQDN")

MAX_SSH_KEYS_PER_USER = getattr(settings, "USERDATA_MAX_SSH_KEYS_PER_USER")
FLAVORS_DISK_TEMPLATES_INFO = \
    getattr(settings, "UI_FLAVORS_DISK_TEMPLATES_INFO", {})
SYSTEM_IMAGES_OWNERS = getattr(settings, "UI_SYSTEM_IMAGES_OWNERS", {})
IMAGE_LISTING_USERS = getattr(settings, "UI_IMAGE_LISTING_USERS", [])
CUSTOM_IMAGE_HELP_URL = getattr(settings, "UI_CUSTOM_IMAGE_HELP_URL", None)

# MEDIA PATHS
UI_MEDIA_URL = \
    getattr(settings, "UI_MEDIA_URL",
            "%sui/static/snf/" % (settings.MEDIA_URL,))
UI_SYNNEFO_IMAGES_URL = \
    getattr(settings,
            "UI_SYNNEFO_IMAGES_URL", UI_MEDIA_URL + "images/")
UI_SYNNEFO_CSS_URL = \
    getattr(settings,
            "UI_SYNNEFO_CSS_URL", UI_MEDIA_URL + "css/")
UI_SYNNEFO_JS_URL = \
    getattr(settings,
            "UI_SYNNEFO_JS_URL", UI_MEDIA_URL + "js/")
UI_SYNNEFO_JS_LIB_URL = \
    getattr(settings,
            "UI_SYNNEFO_JS_LIB_URL", UI_SYNNEFO_JS_URL + "lib/")
UI_SYNNEFO_JS_WEB_URL = \
    getattr(settings, "UI_SYNNEFO_JS_WEB_URL", UI_SYNNEFO_JS_URL + "ui/web/")

# extensions
ENABLE_GLANCE = getattr(settings, 'UI_ENABLE_GLANCE', True)

DIAGNOSTICS_UPDATE_INTERVAL = \
    getattr(settings, 'UI_DIAGNOSTICS_UPDATE_INTERVAL', 2000)

# network settings
DEFAULT_NETWORK_TYPES = {'MAC_FILTERED': 'mac-filtering',
                         'PHYSICAL_VLAN': 'physical-vlan'}
NETWORK_TYPES = \
    getattr(settings,
            'UI_NETWORK_AVAILABLE_NETWORK_TYPES', DEFAULT_NETWORK_TYPES)
DEFAULT_NETWORK_SUBNETS = ['10.0.0.0/24', '192.168.1.1/24']
NETWORK_SUBNETS = \
    getattr(settings,
            'UI_NETWORK_AVAILABLE_SUBNETS', DEFAULT_NETWORK_SUBNETS)
NETWORK_DUPLICATE_NICS = \
    getattr(settings,
            'UI_NETWORK_ALLOW_DUPLICATE_VM_NICS', False)
NETWORK_STRICT_DESTROY = \
    getattr(settings,
            'UI_NETWORK_STRICT_DESTROY', False)
NETWORK_ALLOW_MULTIPLE_DESTROY = \
    getattr(settings,
            'UI_NETWORK_ALLOW_MULTIPLE_DESTROY', False)
AUTOMATIC_NETWORK_RANGE_FORMAT = getattr(settings,
                                         'UI_AUTOMATIC_NETWORK_RANGE_FORMAT',
                                         "192.168.%d.0/24").replace("%d",
                                                                    "{0}")
GROUP_PUBLIC_NETWORKS = getattr(settings, 'UI_GROUP_PUBLIC_NETWORKS', True)

DEFAULT_FORCED_SERVER_NETWORKS = \
    getattr(settings, "CYCLADES_FORCED_SERVER_NETWORKS", [])
FORCED_SERVER_NETWORKS = getattr(settings, "UI_FORCED_SERVER_NETWORKS",
                                 DEFAULT_FORCED_SERVER_NETWORKS)

DEFAULT_HOTPLUG_ENABLED = getattr(settings, "CYCLADES_GANETI_USE_HOTPLUG",
                                  True)
HOTPLUG_ENABLED = getattr(settings, "UI_HOTPLUG_ENABLED",
                          DEFAULT_HOTPLUG_ENABLED)

VOLUME_MAX_SIZE = getattr(settings, "CYCLADES_VOLUME_MAX_SIZE", 200)
SNAPSHOTS_ENABLED = getattr(settings, "CYCLADES_SNAPSHOTS_ENABLED", True)
SHARED_RESOURCES_ENABLED = getattr(settings,
                                   "CYCLADES_SHARED_RESOURCES_ENABLED", False)

def template(name, request, context):
    template_path = os.path.join(os.path.dirname(__file__), "templates/")
    current_template = template_path + name + '.html'
    t = loader.get_template(current_template)
    media_context = {
        'UI_MEDIA_URL': UI_MEDIA_URL,
        'SYNNEFO_JS_URL': UI_SYNNEFO_JS_URL,
        'SYNNEFO_JS_LIB_URL': UI_SYNNEFO_JS_LIB_URL,
        'SYNNEFO_JS_WEB_URL': UI_SYNNEFO_JS_WEB_URL,
        'SYNNEFO_IMAGES_URL': UI_SYNNEFO_IMAGES_URL,
        'SYNNEFO_CSS_URL': UI_SYNNEFO_CSS_URL,
        'SYNNEFO_JS_LIB_VERSION': SYNNEFO_JS_LIB_VERSION,
        'DEBUG': settings.DEBUG
    }
    context.update(media_context)
    return HttpResponse(t.render(RequestContext(request, context)))


def home(request):
    context = {
        'timeout': TIMEOUT,
        'project': '+nefo',
        'request': request,
        'current_lang': get_language() or 'en',
        'compute_api_url': json.dumps(uisettings.COMPUTE_URL),
        'volume_api_url': json.dumps(uisettings.VOLUME_URL),
        'network_api_url': json.dumps(uisettings.NETWORK_URL),
        'user_catalog_url': json.dumps(uisettings.USER_CATALOG_URL),
        'feedback_post_url': json.dumps(uisettings.FEEDBACK_URL),
        'accounts_api_url': json.dumps(uisettings.ACCOUNT_URL),
        'logout_redirect': json.dumps(uisettings.LOGOUT_REDIRECT),
        'login_redirect': json.dumps(uisettings.LOGIN_URL),
        'glance_api_url': json.dumps(uisettings.GLANCE_URL),
        'translate_uuids': json.dumps(True),
        # update interval settings
        'update_interval': UPDATE_INTERVAL,
        'update_interval_increase': UPDATE_INTERVAL_INCREASE,
        'update_interval_increase_after_calls':
        UPDATE_INTERVAL_INCREASE_AFTER_CALLS_COUNT,
        'update_interval_fast': UPDATE_INTERVAL_FAST,
        'update_interval_max': UPDATE_INTERVAL_MAX,
        'changes_since_alignment': CHANGES_SINCE_ALIGNMENT,
        'image_icons': IMAGE_ICONS,
        'auth_cookie_name': AUTH_COOKIE_NAME,
        'auth_skip_redirects': json.dumps(AUTH_SKIP_REDIRECTS),
        'suggested_flavors': json.dumps(SUGGESTED_FLAVORS),
        'suggested_roles': json.dumps(SUGGESTED_ROLES),
        'vm_image_common_metadata': json.dumps(VM_IMAGE_COMMON_METADATA),
        'synnefo_version': SYNNEFO_JS_LIB_VERSION,
        'delay_on_blur': json.dumps(DELAY_ON_BLUR),
        'update_hidden_views': json.dumps(UPDATE_HIDDEN_VIEWS),
        'handle_window_exceptions': json.dumps(HANDLE_WINDOW_EXCEPTIONS),
        'skip_timeouts': json.dumps(SKIP_TIMEOUTS),
        'vm_name_template': json.dumps(VM_NAME_TEMPLATE),
        'flavors_disk_templates_info': json.dumps(FLAVORS_DISK_TEMPLATES_INFO),
        'ssh_support_osfamily_exclude_list': json.dumps(SSH_SUPPORT_OSFAMILY_EXCLUDE_LIST),
        'unknown_os': json.dumps(UNKNOWN_OS),
        'os_created_users': json.dumps(OS_CREATED_USERS),
        'userdata_keys_limit': json.dumps(MAX_SSH_KEYS_PER_USER),
        'use_glance': json.dumps(ENABLE_GLANCE),
        'system_images_owners': json.dumps(SYSTEM_IMAGES_OWNERS),
        'image_listing_users': json.dumps(IMAGE_LISTING_USERS),
        'custom_image_help_url': CUSTOM_IMAGE_HELP_URL,
        'image_deleted_title': json.dumps(IMAGE_DELETED_TITLE),
        'image_deleted_size_title': json.dumps(IMAGE_DELETED_SIZE_TITLE),
        'network_suggested_subnets': json.dumps(NETWORK_SUBNETS),
        'network_available_types': json.dumps(NETWORK_TYPES),
        'forced_server_networks': json.dumps(FORCED_SERVER_NETWORKS),
        'network_allow_duplicate_vm_nics': json.dumps(NETWORK_DUPLICATE_NICS),
        'network_strict_destroy': json.dumps(NETWORK_STRICT_DESTROY),
        'network_allow_multiple_destroy':
        json.dumps(NETWORK_ALLOW_MULTIPLE_DESTROY),
        'automatic_network_range_format':
        json.dumps(AUTOMATIC_NETWORK_RANGE_FORMAT),
        'group_public_networks': json.dumps(GROUP_PUBLIC_NETWORKS),
        'hotplug_enabled': json.dumps(HOTPLUG_ENABLED),
        'diagnostics_update_interval': json.dumps(DIAGNOSTICS_UPDATE_INTERVAL),
        'no_fqdn_message': json.dumps(NO_FQDN_MESSAGE),
        'volume_max_size': json.dumps(VOLUME_MAX_SIZE),
        'snapshots_enabled': json.dumps(SNAPSHOTS_ENABLED),
        'shared_resources_enabled': json.dumps(SHARED_RESOURCES_ENABLED)
    }
    return template('home', request, context)


def machines_console(request):
    host, port, password = ('', '', '')
    host = request.GET.get('host', '')
    port = request.GET.get('port', '')
    password = request.GET.get('password', '')
    machine = request.GET.get('machine', '')
    machine_hostname = request.GET.get('machine_hostname', '')
    context = {'host': host, 'port': port, 'password': password,
               'machine': machine, 'machine_hostname': machine_hostname}
    return template('machines_console', request, context)


def js_tests(request):
    return template('tests', request, {})


CONNECT_LINUX_LINUX_MESSAGE = \
    _("""A direct connection to this machine can be established using the
<a target="_blank" href="http://en.wikipedia.org/wiki/Secure_Shell">
SSH Protocol</a>.
To do so open a terminal and type the following at the prompt to connect
to your machine:""")
CONNECT_LINUX_WINDOWS_MESSAGE = \
    _("""A direct connection to this machine can be established using
<a target="_blank"
href="http://en.wikipedia.org/wiki/Remote_Desktop_Services">
Remote Desktop Service</a>.
To do so, open the following file with an appropriate \
remote desktop client.""")
CONNECT_LINUX_WINDOWS_SUBMESSAGE = \
    _("""If you don't have a Remote Desktop client already installed,
we suggest the use of <a target="_blank"
href=
"http://sourceforge.net/projects/tsclient/files/latest/download?source=files">
tsclient</a>.<br /><span class="important">IMPORTANT: It may take up to 15
minutes for your Windows VM to become available
after its creation.</span>""")
CONNECT_WINDOWS_LINUX_MESSAGE = \
    _("""A direct connection to this machine can be established using the
<a target="_blank"
href="http://en.wikipedia.org/wiki/Secure_Shell">SSH Protocol</a>.
Open an ssh client such as PuTTY and type the following:""")
CONNECT_WINDOWS_LINUX_SUBMESSAGE = \
    _("""If you do not have an ssh client already installed,
<a target="_blank"
href="http://the.earth.li/~sgtatham/putty/latest/x86/putty.exe">
Download PuTTY</a>""")

CONNECT_WINDOWS_WINDOWS_MESSAGE = \
    _("""A direct connection to this machine can be
established using Remote Desktop. Click on the following link, and if asked
open it using "Remote Desktop Connection".
<br /><span class="important">
IMPORTANT: It may take up to 15 minutes for your Windows VM to become available
after its creation.</span>""")
CONNECT_WINDOWS_WINDOWS_SUBMESSAGE = \
    _("""Save this file to disk for future use.""")

# info/subinfo for all os combinations
#
# [0] info gets displayed on top of the message box
# [1] subinfo gets displayed on the bottom as extra info
# provided to the user when needed
CONNECT_PROMPT_MESSAGES = {
    'linux': {
        'linux': [CONNECT_LINUX_LINUX_MESSAGE, ""],
        'windows': [CONNECT_LINUX_WINDOWS_MESSAGE,
                    CONNECT_LINUX_WINDOWS_SUBMESSAGE],
        'ssh_message': "ssh %(user)s@%(hostname)s",
        'ssh_message_port': "ssh -p %(port)s %(user)s@%(hostname)s"

    },
    'windows': {
        'linux': [CONNECT_WINDOWS_LINUX_MESSAGE,
                  CONNECT_WINDOWS_LINUX_SUBMESSAGE],
        'windows': [CONNECT_WINDOWS_WINDOWS_MESSAGE,
                    CONNECT_WINDOWS_WINDOWS_SUBMESSAGE],
        'ssh_message': "%(user)s@%(hostname)s",
        'ssh_message_port': "%(user)s@%(hostname)s (port: %(port)s)"
    },
}

APPEND_CONNECT_PROMPT_MESSAGES = \
    getattr(settings, 'UI_CONNECT_PROMPT_MESSAGES', {})
for k, v in APPEND_CONNECT_PROMPT_MESSAGES.iteritems():
    CONNECT_PROMPT_MESSAGES[k].update(v)

# retrieve domain prefix from settings
DOMAIN_PREFIX = getattr(settings, 'MACHINE_DOMAIN_PREFIX', getattr(settings,
                        'BACKEND_PREFIX_ID', ""))

# domain template string
DOMAIN_TPL = "%s%%s" % DOMAIN_PREFIX


def machines_connect(request):
    ip_address = request.GET.get('ip_address', '')
    hostname = request.GET.get('hostname', '')
    operating_system = metadata_os = request.GET.get('os', '')
    server_id = request.GET.get('srv', 0)
    host_os = request.GET.get('host_os', 'Linux').lower()
    username = request.GET.get('username', None)
    domain = request.GET.get("domain", DOMAIN_TPL % int(server_id))
    ports = json.loads(request.GET.get('ports', '{}'))

    # guess host os
    if host_os != "windows":
        host_os = 'linux'

    # guess username
    if not username:
        username = "root"

        if metadata_os.lower() in ['ubuntu', 'kubuntu', 'fedora']:
            username = "user"

        if metadata_os.lower() == "windows":
            username = "Administrator"

    ssh_forward = ports.get("22", None)
    rdp_forward = ports.get("3389", None)

    # operating system provides ssh access
    ssh = False
    if operating_system != "windows":
        operating_system = "linux"
        ssh = True

    # rdp param is set, the user requested rdp file
    # check if we are on windows
    if operating_system == 'windows' and request.GET.get("rdp", False):
        port = '3389'
        if rdp_forward:
            hostname = rdp_forward.get('host', hostname)
            ip_address = rdp_forward.get('host', ip_address)
            port = str(rdp_forward.get('port', '3389'))

        extra_rdp_content = ''
        # UI sent domain info (from vm metadata) use this
        # otherwise use our default snf-<vm_id> domain
        EXTRA_RDP_CONTENT = getattr(settings, 'UI_EXTRA_RDP_CONTENT', '')
        if callable(EXTRA_RDP_CONTENT):
            extra_rdp_content = EXTRA_RDP_CONTENT(server_id, ip_address,
                                                  hostname, username)
        else:
            if EXTRA_RDP_CONTENT:
                extra_rdp_content = EXTRA_RDP_CONTENT % \
                    {
                        'server_id': server_id,
                        'ip_address': ip_address,
                        'hostname': hostname,
                        'user': username,
                        'port': port
                    }

        rdp_context = {
            'username': username,
            'domain': domain,
            'ip_address': ip_address,
            'hostname': hostname,
            'port': request.GET.get('port', port),
            'extra_content': extra_rdp_content
        }

        rdp_file_data = render_to_string("synnefo-windows.rdp", rdp_context)
        response = HttpResponse(rdp_file_data, mimetype='application/x-rdp')

        # proper filename, use server id and ip address
        filename = "%d-%s.rdp" % (int(server_id), hostname)
        response['Content-Disposition'] = 'attachment; filename=%s' % filename
    else:
        message_key = "ssh_message"
        ip_address = ip_address
        hostname = hostname
        port = ''
        if ssh_forward:
            message_key = 'ssh_message_port'
            hostname = ssh_forward.get('host', hostname)
            ip_address = ssh_forward.get('host', ip_address)
            port = str(ssh_forward.get('port', '22'))

        ssh_message = CONNECT_PROMPT_MESSAGES['linux'].get(message_key)
        if host_os == 'windows':
            ssh_message = CONNECT_PROMPT_MESSAGES['windows'].get(message_key)
        if callable(ssh_message):
            link_title = ssh_message(server_id, ip_address, hostname, username)
        else:
            link_title = ssh_message % {
                'server_id': server_id,
                'ip_address': ip_address,
                'hostname': hostname,
                'user': username,
                'port': port
            }
        if (operating_system != "windows"):
            link_url = None

        else:
            link_title = _("Remote desktop to %s") % ip_address
            if rdp_forward:
                hostname = rdp_forward.get('host', hostname)
                ip_address = rdp_forward.get('host', ip_address)
                port = str(rdp_forward.get('port', '3389'))
                link_title = _("Remote desktop to %s (port %s)") % (ip_address,
                                                                    port)
            link_url = \
                "%s?ip_address=%s&os=%s&rdp=1&srv=%d&username=%s&domain=%s" \
                "&hostname=%s&port=%s" % (
                    reverse("ui_machines_connect"), ip_address,
                    operating_system, int(server_id), username,
                    domain, hostname, port)

        # try to find a specific message
        try:
            connect_message = \
                CONNECT_PROMPT_MESSAGES[host_os][operating_system][0]
            subinfo = CONNECT_PROMPT_MESSAGES[host_os][operating_system][1]
        except KeyError:
            connect_message = \
                _("You are trying to connect from a %s "
                  "machine to a %s machine") % (host_os, operating_system)
            subinfo = ""

        response_object = {
            'ip': ip_address,
            'os': operating_system,
            'ssh': ssh,
            'info': unicode(connect_message),
            'subinfo': unicode(subinfo),
            'link': {'title': unicode(link_title), 'url': link_url}
        }
        response = \
            HttpResponse(json.dumps(response_object),
                         mimetype='application/json')  # no windows, no rdp

    return response
