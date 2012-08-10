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
#

import os

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.template import Context, loader
from django.http import HttpResponse
from django.utils.translation import get_language
from django.utils import simplejson as json
from django.shortcuts import render_to_response
from django.template.loader import render_to_string
from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from django.http import Http404
from django.template import RequestContext

from synnefo.util.version import get_component_version

from synnefo.lib.astakos import get_user

SYNNEFO_JS_LIB_VERSION = get_component_version('app')

# api configuration
COMPUTE_API_URL = getattr(settings, 'COMPUTE_API_URL', '/api/v1.1')

# UI preferences settings
TIMEOUT = getattr(settings, "TIMEOUT", 10000)
UPDATE_INTERVAL = getattr(settings, "UI_UPDATE_INTERVAL", 5000)
UPDATE_INTERVAL_INCREASE = getattr(settings, "UI_UPDATE_INTERVAL_INCREASE", 500)
UPDATE_INTERVAL_INCREASE_AFTER_CALLS_COUNT = getattr(settings,
                                "UI_UPDATE_INTERVAL_INCREASE_AFTER_CALLS_COUNT",
                                3)
UPDATE_INTERVAL_FAST = getattr(settings, "UI_UPDATE_INTERVAL_FAST", 2500)
UPDATE_INTERVAL_MAX = getattr(settings, "UI_UPDATE_INTERVAL_MAX", 10000)

# predefined values settings
VM_IMAGE_COMMON_METADATA = getattr(settings, "UI_VM_IMAGE_COMMON_METADATA", ["OS", "users"])
SUGGESTED_FLAVORS_DEFAULT = {}
SUGGESTED_FLAVORS = getattr(settings, "VM_CREATE_SUGGESTED_FLAVORS",
                            SUGGESTED_FLAVORS_DEFAULT)
SUGGESTED_ROLES_DEFAULT = ["Database server", "File server", "Mail server",
                           "Web server", "Proxy"]
SUGGESTED_ROLES = getattr(settings, "VM_CREATE_SUGGESTED_ROLES",
                          SUGGESTED_ROLES_DEFAULT)
IMAGE_ICONS = settings.IMAGE_ICONS
IMAGE_DELETED_TITLE = getattr(settings, 'UI_IMAGE_DELETED_TITLE',
                            '(deleted)')
IMAGE_DELETED_SIZE_TITLE = getattr(settings, 'UI_IMAGE_DELETED_SIZE_TITLE',
                            '(none)')

SUPPORT_SSH_OS_LIST = getattr(settings, "UI_SUPPORT_SSH_OS_LIST",)
OS_CREATED_USERS = getattr(settings, "UI_OS_DEFAULT_USER_MAP")
LOGOUT_URL = getattr(settings, "UI_LOGOUT_URL", '/im/authenticate')
LOGIN_URL = getattr(settings, "UI_LOGIN_URL", '/im/login')
AUTH_COOKIE_NAME = getattr(settings, "UI_AUTH_COOKIE_NAME", 'synnefo_user')

# UI behaviour settings
DELAY_ON_BLUR = getattr(settings, "UI_DELAY_ON_BLUR", True)
UPDATE_HIDDEN_VIEWS = getattr(settings, "UI_UPDATE_HIDDEN_VIEWS", False)
HANDLE_WINDOW_EXCEPTIONS = getattr(settings, "UI_HANDLE_WINDOW_EXCEPTIONS", True)
SKIP_TIMEOUTS = getattr(settings, "UI_SKIP_TIMEOUTS", 1)

# Additional settings
VM_NAME_TEMPLATE = getattr(settings, "VM_CREATE_NAME_TPL", "My {0} server")
MAX_SSH_KEYS_PER_USER = getattr(settings, "USERDATA_MAX_SSH_KEYS_PER_USER")
FLAVORS_DISK_TEMPLATES_INFO = getattr(settings, "UI_FLAVORS_DISK_TEMPLATES_INFO", {})
SYSTEM_IMAGES_OWNERS = getattr(settings, "UI_SYSTEM_IMAGES_OWNERS", {})

# MEDIA PATHS
UI_MEDIA_URL = getattr(settings, "UI_MEDIA_URL",
                    "%ssnf-%s/" % (settings.MEDIA_URL, SYNNEFO_JS_LIB_VERSION))
UI_SYNNEFO_IMAGES_URL = getattr(settings,
                    "UI_SYNNEFO_IMAGES_URL", UI_MEDIA_URL + "images/")
UI_SYNNEFO_CSS_URL = getattr(settings,
                    "UI_SYNNEFO_CSS_URL", UI_MEDIA_URL + "css/")
UI_SYNNEFO_JS_URL = getattr(settings,
                    "UI_SYNNEFO_JS_URL", UI_MEDIA_URL + "js/")
UI_SYNNEFO_JS_LIB_URL = getattr(settings,
                    "UI_SYNNEFO_JS_LIB_URL", UI_SYNNEFO_JS_URL + "lib/")
UI_SYNNEFO_JS_WEB_URL = getattr(settings,
                    "UI_SYNNEFO_JS_WEB_URL",
                    UI_SYNNEFO_JS_URL + "ui/web/")

# extensions
ENABLE_GLANCE = getattr(settings, 'UI_ENABLE_GLANCE', True)
GLANCE_API_URL = getattr(settings, 'UI_GLANCE_API_URL', '/glance')
FEEDBACK_CONTACTS = getattr(settings, "FEEDBACK_CONTACTS", [])
FEEDBACK_EMAIL_FROM = settings.FEEDBACK_EMAIL_FROM
DIAGNOSTICS_UPDATE_INTERVAL = getattr(settings,
                'UI_DIAGNOSTICS_UPDATE_INTERVAL', 2000)

# network settings
DEFAULT_NETWORK_TYPES = {'PRIVATE_FILTERED': 'mac-filtering'}
NETWORK_TYPES = getattr(settings,
                    'UI_NETWORK_AVAILABLE_NETWORK_TYPES', DEFAULT_NETWORK_TYPES)
DEFAULT_NETWORK_SUBNETS = ['10.0.0.0/24', '192.168.1.1/24']
NETWORK_SUBNETS = getattr(settings,
                    'UI_NETWORK_AVAILABLE_SUBNETS', DEFAULT_NETWORK_SUBNETS)
NETWORK_DUPLICATE_NICS = getattr(settings,
                    'UI_NETWORK_ALLOW_DUPLICATE_VM_NICS', False)
NETWORK_STRICT_DESTROY = getattr(settings,
                    'UI_NETWORK_STRICT_DESTROY', False)
NETWORK_ALLOW_MULTIPLE_DESTROY = getattr(settings,
                    'UI_NETWORK_ALLOW_MULTIPLE_DESTROY', False)

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
    context = {'timeout': TIMEOUT,
               'project': '+nefo',
               'request': request,
               'current_lang': get_language() or 'en',
               'compute_api_url': json.dumps(COMPUTE_API_URL),
                # update interval settings
               'update_interval': UPDATE_INTERVAL,
               'update_interval_increase': UPDATE_INTERVAL_INCREASE,
               'update_interval_increase_after_calls': UPDATE_INTERVAL_INCREASE_AFTER_CALLS_COUNT,
               'update_interval_fast': UPDATE_INTERVAL_FAST,
               'update_interval_max': UPDATE_INTERVAL_MAX,
                # additional settings
               'image_icons': IMAGE_ICONS,
               'logout_redirect': LOGOUT_URL,
               'login_redirect': LOGIN_URL,
               'auth_cookie_name': AUTH_COOKIE_NAME,
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
               'support_ssh_os_list': json.dumps(SUPPORT_SSH_OS_LIST),
               'os_created_users': json.dumps(OS_CREATED_USERS),
               'userdata_keys_limit': json.dumps(MAX_SSH_KEYS_PER_USER),
               'use_glance': json.dumps(ENABLE_GLANCE),
               'glance_api_url': json.dumps(GLANCE_API_URL),
               'system_images_owners': json.dumps(SYSTEM_IMAGES_OWNERS),
               'image_deleted_title': json.dumps(IMAGE_DELETED_TITLE),
               'image_deleted_size_title': json.dumps(IMAGE_DELETED_SIZE_TITLE),
               'network_suggested_subnets': json.dumps(NETWORK_SUBNETS),
               'network_available_types': json.dumps(NETWORK_TYPES),
               'network_allow_duplicate_vm_nics': json.dumps(NETWORK_DUPLICATE_NICS),
               'network_strict_destroy': json.dumps(NETWORK_STRICT_DESTROY),
               'network_allow_multiple_destroy': json.dumps(NETWORK_ALLOW_MULTIPLE_DESTROY),
               'diagnostics_update_interval': json.dumps(DIAGNOSTICS_UPDATE_INTERVAL)
    }
    return template('home', request, context)

def machines_console(request):
    host, port, password = ('','','')
    host = request.GET.get('host','')
    port = request.GET.get('port','')
    password = request.GET.get('password','')
    machine = request.GET.get('machine','')
    host_ip = request.GET.get('host_ip','')
    host_ip_v6 = request.GET.get('host_ip_v6','')
    context = {'host': host, 'port': port, 'password': password,
               'machine': machine, 'host_ip': host_ip, 'host_ip_v6': host_ip_v6}
    return template('machines_console', request, context)

def js_tests(request):
    return template('tests', request, {})

CONNECT_LINUX_LINUX_MESSAGE = _("""A direct connection to this machine can be established using the <a target="_blank"
href="http://en.wikipedia.org/wiki/Secure_Shell">SSH Protocol</a>.
To do so open a terminal and type the following at the prompt to connect to your machine:""")
CONNECT_LINUX_WINDOWS_MESSAGE = _("""A direct connection to this machine can be
established using <a target="_blank" href="http://en.wikipedia.org/wiki/Remote_Desktop_Services">Remote Desktop Service</a>.
To do so, open the following file with an appropriate remote desktop client.
""")
CONNECT_LINUX_WINDOWS_SUBMESSAGE = _("""If you don't have a Remote Desktop client already installed,
we suggest the use of <a target="_blank"
href="http://sourceforge.net/projects/tsclient/files/latest/download?source=files">tsclient</a>.<br
/><span class="important">IMPORTANT: It may take up to 15 minutes for your Windows VM to become available
after its creation.</span>""")
CONNECT_WINDOWS_LINUX_MESSAGE = _("""A direct connection to this machine can be established using the <a target="_blank"
href="http://en.wikipedia.org/wiki/Secure_Shell">SSH Protocol</a>.
Open an ssh client such as PuTTY and type the following:""")
CONNECT_WINDOWS_LINUX_SUBMESSAGE = _("""If you do not have an ssh client already installed,
<a target="_blank" href="http://the.earth.li/~sgtatham/putty/latest/x86/putty.exe">Download PuTTY</a>""")

CONNECT_WINDOWS_WINDOWS_MESSAGE = _("""A direct connection to this machine can be
established using Remote Desktop. Click on the following link, and if asked
open it using "Remote Desktop Connection".
IMPORTANT: It may take up to 15 minutes for your Windows VM to become available
after its creation.""")
CONNECT_WINDOWS_WINDOWS_SUBMESSAGE = _("""Save this file to disk for future use""")

# info/subinfo for all os combinations
#
# [0] info gets displayed on top of the message box
# [1] subinfo gets displayed on the bottom as extra info
# provided to the user when needed
CONNECT_PROMPT_MESSAGES = {
    'linux': {
            'linux': [CONNECT_LINUX_LINUX_MESSAGE, ""],
            'windows': [CONNECT_LINUX_WINDOWS_MESSAGE,
                        CONNECT_LINUX_WINDOWS_SUBMESSAGE]
        },
    'windows': {
            'linux': [CONNECT_WINDOWS_LINUX_MESSAGE,
                      CONNECT_WINDOWS_LINUX_SUBMESSAGE],
            'windows': [CONNECT_WINDOWS_WINDOWS_MESSAGE,
                        CONNECT_WINDOWS_WINDOWS_SUBMESSAGE]
        }
    }

# retrieve domain prefix from settings
DOMAIN_PREFIX = getattr(settings, 'MACHINE_DOMAIN_PREFIX', getattr(settings,
                        'BACKEND_PREFIX_ID', ""))

# domain template string
DOMAIN_TPL = "%s%%s" % DOMAIN_PREFIX

def machines_connect(request):
    ip_address = request.GET.get('ip_address','')
    operating_system = metadata_os = request.GET.get('os','')
    server_id = request.GET.get('srv', 0)
    host_os = request.GET.get('host_os','Linux').lower()
    username = request.GET.get('username', None)
    domain = request.GET.get("domain", DOMAIN_TPL % int(server_id))

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

    # operating system provides ssh access
    ssh = False
    if operating_system != "windows":
        operating_system = "linux"
        ssh = True

    # rdp param is set, the user requested rdp file
    # check if we are on windows
    if operating_system == 'windows' and request.GET.get("rdp", False):

        # UI sent domain info (from vm metadata) use this
        # otherwise use our default snf-<vm_id> domain
        rdp_context = {
                'username': username,
                'domain': domain,
                'ip_address': ip_address
        }

        rdp_file_data = render_to_string("synnefo-windows.rdp", rdp_context)
        response = HttpResponse(rdp_file_data, mimetype='application/x-rdp')

        # proper filename, use server id and ip address
        filename = "%d-%s.rdp" % (int(server_id), ip_address)
        response['Content-Disposition'] = 'attachment; filename=%s' % filename
    else:
        link_title = _("Remote desktop to %s") % ip_address
        link_url = "%s?ip_address=%s&os=%s&rdp=1&srv=%d&username=%s&domain=%s" % (
                reverse("ui_machines_connect"), ip_address, operating_system,int(server_id), username, domain)

        if (operating_system != "windows"):
            link_title = "ssh %s@%s" % (username, ip_address)
            link_url = None

            if host_os == "windows":
                link_title = "%s@%s" % (username, ip_address)

        # try to find a specific message
        try:
            connect_message = CONNECT_PROMPT_MESSAGES[host_os][operating_system][0]
            subinfo = CONNECT_PROMPT_MESSAGES[host_os][operating_system][1]
        except KeyError:
            connect_message = _("You are trying to connect from a %s "
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
        response = HttpResponse(json.dumps(response_object),
                                mimetype='application/json')  #no windows, no rdp

    return response

def feedback_submit(request):
    if not request.method == "POST":
        raise Http404

    # fill request object with astakos user information
    get_user(request, settings.ASTAKOS_URL)

    message = request.POST.get("feedback-msg")
    data = request.POST.get("feedback-data")

    # default to True (calls from error pages)
    allow_data_send = request.POST.get("feedback-submit-data", True)

    mail_subject = unicode(_("Feedback from synnefo application"))

    mail_context = {'message': message, 'data': data,
                    'allow_data_send': allow_data_send, 'request': request}
    mail_content = render_to_string("feedback_mail.txt", mail_context)

    send_mail(mail_subject, mail_content, FEEDBACK_EMAIL_FROM,
            dict(FEEDBACK_CONTACTS).values(), fail_silently=False)

    return HttpResponse('{"status":"send"}');

