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
from django.core.urlresolvers import reverse

TIMEOUT = settings.TIMEOUT
UPDATE_INTERVAL = settings.UPDATE_INTERVAL
IMAGE_ICONS = settings.IMAGE_ICONS

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
               'image_icons': IMAGE_ICONS,}
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
    context = {'host': host, 'port': port, 'password': password, 'machine': machine, 'host_ip': host_ip}
    return template('machines_console', context)


CONNECT_LINUX_LINUX_MESSAGE = _("Trying to connect from linux to linux")
CONNECT_LINUX_WINDOWS_MESSAGE = _("Trying to connect from linux to windows")
CONNECT_WINDOWS_LINUX_MESSAGE = _("Trying to connect from windows to linux")
CONNECT_WINDOWS_WINDOWS_MESSAGE = _("Trying to connect from windows to windows")

CONNECT_PROMT_MESSAGES = {
    'linux': {
            'linux': CONNECT_LINUX_LINUX_MESSAGE,
            'windows': CONNECT_LINUX_WINDOWS_MESSAGE
        },
    'windows': {
            'linux': CONNECT_WINDOWS_LINUX_MESSAGE,
            'windows': CONNECT_WINDOWS_WINDOWS_MESSAGE
        }
    }

def machines_connect(request):
    ip_address = request.GET.get('ip_address','')
    operating_system = request.GET.get('os','')
    host_os = request.GET.get('host_os','Linux').lower()

    if operating_system != "windows":
        operating_system = "linux"

    if operating_system == 'windows' and request.GET.get("rdp", False): #check if we are on windows
        rdp_file = os.path.join(os.path.dirname(__file__), "static/") + 'synnefo-windows.rdp'
        connect_data = open(rdp_file, 'r').read()
        connect_data = connect_data + 'full address:s:' + ip_address + '\n'
        response = HttpResponse(connect_data, mimetype='application/x-rdp')
        response['Content-Disposition'] = 'attachment; filename=synnefo-windows.rdp'
    else:
        ssh = False
        if (operating_system != "windows"):
            ssh = True

        info = _("Connect on windows using the following RDP shortcut file")
        link_title = _("Windows RDP shortcut file")
        link_url = "%s?ip_address=%s&os=%s&rdp=1" % (reverse("machines-connect"), ip_address, operating_system)

        if (operating_system != "windows"):
            info = _("Connect on linux machine using the following url")
            link_url = "ssh://%s/" % ip_address
            link_title = link_url

        # try to find a specific message
        try:
            connect_message = CONNECT_PROMT_MESSAGES[host_os][operating_system]
        except KeyError:
            connect_message = _("You are trying to connect from a %s machine to a %s machine") % (host_os, operating_system)

        response_object = {
                'ip': ip_address,
                'os': operating_system,
                'ssh': ssh,
                'info': unicode(connect_message),
                'link': {'title': unicode(link_title), 'url': link_url}
            }
        response = HttpResponse(json.dumps(response_object), mimetype='application/json')  #no windows, no rdp

    return response


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
