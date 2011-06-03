import os
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.template import Context, loader
from django.http import HttpResponse
from django.utils.translation import get_language
from django.utils import simplejson as json
from django.shortcuts import render_to_response

TIMEOUT = settings.TIMEOUT
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
