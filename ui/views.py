import os
from django.utils.translation import gettext_lazy as _
from django.template import Context, loader
from django.http import HttpResponse
from django.utils.translation import get_language


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
