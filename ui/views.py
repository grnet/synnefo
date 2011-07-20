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

from synnefo.logic.email_send import send_async

from django.http import Http404

TIMEOUT = settings.TIMEOUT
UPDATE_INTERVAL = settings.UPDATE_INTERVAL
IMAGE_ICONS = settings.IMAGE_ICONS
LOGOUT_URL = getattr(settings, "LOGOUT_URL", settings.LOGIN_URL)

def template(name, context):
    template_path = os.path.join(os.path.dirname(__file__), "templates/")
    current_template = template_path + name + '.html'
    t = loader.get_template(current_template)
    return HttpResponse(t.render(Context(context)))

def home(request):
    context = {'timeout': TIMEOUT,
               'project': '+nefo',
               'request': request,
               'current_lang': get_language() or 'en',
               'update_interval': UPDATE_INTERVAL,
               'image_icons': IMAGE_ICONS,
               'logout_redirect': LOGOUT_URL,
               'DEBUG': settings.DEBUG}
    return template('home', context)

def machines(request):
    context = {'default_keywords': settings.DEFAULT_KEYWORDS}
    return template('machines', context)

def machines_icon(request):
    context = {'default_keywords': settings.DEFAULT_KEYWORDS}
    return template('machines_icon', context)

def machines_list(request):
    context = {'default_keywords': settings.DEFAULT_KEYWORDS}
    return template('machines_list', context)

def machines_single(request):
    context = {'default_keywords': settings.DEFAULT_KEYWORDS}
    return template('machines_single', context)

def machines_console(request):
    host, port, password = ('','','')
    host = request.GET.get('host','')
    port = request.GET.get('port','')
    password = request.GET.get('password','')
    machine = request.GET.get('machine','')
    host_ip = request.GET.get('host_ip','')
    host_ip_v6 = request.GET.get('host_ip_v6','')
    context = {'host': host, 'port': port, 'password': password, 'machine': machine, 'host_ip': host_ip, 'host_ip_v6': host_ip_v6}
    return template('machines_console', context)


CONNECT_LINUX_LINUX_MESSAGE = _("""A direct connection to this machine can be established using the <a target="_blank"
href="http://en.wikipedia.org/wiki/Secure_Shell">SSH Protocol</a>.
To do so open a terminal and type the following at the prompt to connect to your machine:""")
CONNECT_LINUX_WINDOWS_MESSAGE = _("""A direct connection to this machine can be
established using <a target="_blank" href="http://en.wikipedia.org/wiki/Remote_Desktop_Services">Remote Desktop Service</a>.
To do so, open the following file with an appropriate remote desktop client.""")
CONNECT_LINUX_WINDOWS_SUBMESSAGE = _("""If you don't have one already
installed, we suggest the use of <a target="_blank" href="http://sourceforge.net/projects/tsclient/files/tsclient/tsclient-unstable/tsclient-2.0.1.tar.bz2/download">tsclient</a>.""")

CONNECT_WINDOWS_LINUX_MESSAGE = _("""A direct connection to this machine can be established using the <a target="_blank"
href="http://en.wikipedia.org/wiki/Secure_Shell">SSH Protocol</a>.
Open an ssh client such as PuTTY and type the following:""")
CONNECT_WINDOWS_LINUX_SUBMESSAGE = _("""If you do not have an ssh client already installed,
<a target="_blank" href="http://the.earth.li/~sgtatham/putty/latest/x86/putty.exe">Download PuTTY</a>""")
CONNECT_WINDOWS_WINDOWS_MESSAGE = _("Trying to connect from windows to windows")


# info/subinfo for all os combinations
#
# [0] info gets displayed on top of the message box
# [1] subinfo gets displayed on the bottom as extra info
# provided to the user when needed
CONNECT_PROMT_MESSAGES = {
    'linux': {
            'linux': [CONNECT_LINUX_LINUX_MESSAGE, ""],
            'windows': [CONNECT_LINUX_WINDOWS_MESSAGE, CONNECT_LINUX_WINDOWS_SUBMESSAGE]
        },
    'windows': {
            'linux': [CONNECT_WINDOWS_LINUX_MESSAGE, CONNECT_WINDOWS_LINUX_SUBMESSAGE],
            'windows': [CONNECT_WINDOWS_WINDOWS_MESSAGE, ""]
        }
    }

def machines_connect(request):
    ip_address = request.GET.get('ip_address','')
    operating_system = metadata_os = request.GET.get('os','')
    server_id = request.GET.get('srv', 0)
    host_os = request.GET.get('host_os','Linux').lower()
    username = request.GET.get('username', None)

    if host_os != "windows":
        host_os = 'linux'

    if operating_system != "windows":
        operating_system = "linux"

    # rdp param is set, the user requested rdp file
    if operating_system == 'windows' and request.GET.get("rdp", False): #check if we are on windows
        rdp_file = os.path.join(os.path.dirname(__file__), "static/") + 'synnefo-windows.rdp'
        connect_data = open(rdp_file, 'r').read()
        connect_data = connect_data + 'full address:s:' + ip_address + '\n'
        response = HttpResponse(connect_data, mimetype='application/x-rdp')

        # proper filename, use server id and ip address
        filename = "%d-%s.rdp" % (int(server_id), ip_address)
        response['Content-Disposition'] = 'attachment; filename=%s' % filename
    else:
        # no rdp requested return json object with info on how to connect
        ssh = False
        if (operating_system != "windows"):
            ssh = True

        link_title = _("Remote desktop to %s") % ip_address
        link_url = "%s?ip_address=%s&os=%s&rdp=1&srv=%d" % (reverse("machines-connect"), ip_address, operating_system,
                int(server_id))

        user = username
        if not user:
            user = "root"
            if metadata_os.lower() in ['ubuntu', 'kubuntu', 'fedora']:
                user = "user"

        if (operating_system != "windows"):
            link_title = "ssh %s@%s" % (user, ip_address)
            link_url = None

            if host_os == "windows":
                link_title = "%s@%s" % (user, ip_address)

        # try to find a specific message
        try:
            connect_message = CONNECT_PROMT_MESSAGES[host_os][operating_system][0]
            subinfo = CONNECT_PROMT_MESSAGES[host_os][operating_system][1]
        except KeyError:
            connect_message = _("You are trying to connect from a %s machine to a %s machine") % (host_os, operating_system)
            subinfo = ""

        response_object = {
                'ip': ip_address,
                'os': operating_system,
                'ssh': ssh,
                'info': unicode(connect_message),
                'subinfo': unicode(subinfo),
                'link': {'title': unicode(link_title), 'url': link_url}
            }
        response = HttpResponse(json.dumps(response_object), mimetype='application/json')  #no windows, no rdp

    return response

FEEDBACK_CONTACTS = getattr(settings, "FEEDBACK_CONTACTS", [])
FEEDBACK_EMAIL_FROM = settings.FEEDBACK_EMAIL_FROM

def feedback_submit(request):

    if not request.method == "POST":
        raise Http404

    message = request.POST.get("feedback-msg")
    data = request.POST.get("feedback-data")

    # default to True (calls from error pages)
    allow_data_send = request.POST.get("feedback-submit-data", True)

    mail_subject = unicode(_("Feedback from synnefo application"))

    mail_context = {'message': message, 'data': data, 'allow_data_send': allow_data_send, 'request': request}
    mail_content = render_to_string("feedback_mail.txt", mail_context)

    if settings.DEBUG:
        print mail_subject, mail_content

    for email in FEEDBACK_CONTACTS:
        send_async(
                frm = FEEDBACK_EMAIL_FROM,
                to = "%s <%s>" % (email[0], email[1]),
                subject = mail_subject,
                body = mail_content
        )

    return HttpResponse("ok");

def images(request):
    context = {}
    return template('images', context)

def disks(request):
    context = {}
    return template('disks', context)

def networks(request):
    context = {}
    return template('networks', context)

def files(request):
    context = {}
    return template('files', context)

def desktops(request):
    context = {}
    return template('desktops', context)

def apps(request):
    context = {}
    return template('apps', context)
