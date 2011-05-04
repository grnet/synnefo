import os
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.template import Context, loader
from django.http import HttpResponse
from django.utils.translation import get_language
from django.utils import simplejson as json

TIMEOUT = settings.TIMEOUT
CONSOLE_WIDTH = 800 #settings.CONSOLE_WIDTH
CONSOLE_HEIGHT = 600 #settings.CONSOLE_HEIGHT

def template(name, context):
    template_path = os.path.join(os.path.dirname(__file__), "templates/")
    current_template = template_path + name + '.html'
    t = loader.get_template(current_template)
    return HttpResponse(t.render(Context(context)))


def home(request):
    context = {'timeout': TIMEOUT,
               'project': '+nefo',
               'request': request,
               'current_lang': get_language() or 'en'}
    return template('home', context)


def machines(request):
    context = {}
    return template('machines', context)

def machine_console(request):
    host, port, password = ('','','')
    host = request.GET.get('host','')
    port = request.GET.get('port','')
    password = request.GET.get('password','')
    context = {'host': host, 'port': port, 'password': password,
    'console_height': CONSOLE_HEIGHT, 'console_width': CONSOLE_WIDTH}
    return template('machine_console', context)

def machines_standard(request):
    context = {}
    return template('standard', context)


def machines_list(request):
    context = {}
    return template('list', context)


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
