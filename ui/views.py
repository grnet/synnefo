import os
from django.utils.translation import gettext_lazy as _
from django.template import Context, loader
from django.http import HttpResponse
from django.utils.translation import get_language

DEFAULT_IMAGES = [
              {'id': 'ubuntu-10.10-x86_64-server', 'type':'standard', 'title': 'Ubuntu 10.10 server 64bit', 'description': _('Apache, MySQL, php5 preinstalled'), 'size': '834', 'logo':'ubuntu.png'}, 
              {'id': 'fedora-14-desktop', 'type':'standard', 'title': 'Fedora 14 desktop 32bit', 'description': 'Apache, MySQL, php5 preinstalled', 'size': '912', 'logo':'fedora.png'}, 
              {'id': 'windows7-pro', 'type':'standard', 'title': 'Windows 7 professional', 'description': 'MS Office 7 preinstalled', 'size': '8142', 'logo':'windows.png'}, 
              {'id': 'windows-xp', 'type':'standard', 'title': 'Windows XP', 'description': 'MS Office XP preinstalled', 'size': '6192', 'logo':'windows.png'},
              {'id': 'netbsd-server', 'type':'custom', 'title': 'NetBSD server', 'description': 'my secure torrent server', 'size': '898', 'logo':'netbsd.png'}, 
              {'id': 'gentoo-playroom', 'type':'custom', 'title': 'Centoo', 'description': 'online pinaball olympiad server', 'size': '912', 'logo':'gentoo.png'},  
             ]

DEFAULT_NODES = [
                 {'id':1, 'name':'My mail server', 'state':'3','public_ip':'147.102.1.62', 'thumb' : 'ubuntu.png'},
                 {'id':2, 'name':'My name server', 'state':'3','public_ip':'147.102.1.64', 'thumb' : 'debian.png'},
                 {'id':3, 'name':'My file server', 'state':'3','public_ip':'147.102.1.65', 'thumb' : 'ubuntu.png'},
                 {'id':4, 'name':'My torrent server', 'state':'3','public_ip':'147.102.1.66', 'thumb' : 'gentoo.png'},
                 {'id':5, 'name':'My firewall', 'state':'3','public_ip':'147.102.1.67', 'thumb' : 'netbsd.png'},
                 {'id':6, 'name':'My windows workstation', 'state':'0','public_ip':'147.102.1.69', 'thumb' : 'windows-off.png'},
                ]

def template(name, context):
    template_path = os.path.join(os.path.dirname(__file__), "templates/")  
    current_template = template_path + name + '.html'
    t = loader.get_template(current_template)
    return HttpResponse(t.render(Context(context)))

def home(request):
    context = { 'project' : '+nefo', 'request': request, 'current_lang' : get_language() or 'en' }
    return template('home', context)

def instances(request):
    context = {}
    return template('instances', context)
   
def instances_list(request):
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
