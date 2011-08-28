from functools import wraps

from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string

from synnefo.db import models
from synnefo.invitations.invitations import add_invitation, send_invitation


def render(template, tab, **kwargs):
    kwargs.setdefault('tab', tab)
    return render_to_string(template, kwargs)


def index(request):
    html = render('index.html', 'home')
    return HttpResponse(html)


def flavors_list(request):
    flavors = models.Flavor.objects.order_by('id')
    html = render('flavors_list.html', 'flavors', flavors=flavors)
    return HttpResponse(html)

def flavors_create(request):
    if request.method == 'GET':
        html = render('flavors_create.html', 'flavors')
        return HttpResponse(html)
    if request.method == 'POST':
        flavor = models.Flavor()
        flavor.cpu = request.POST.get('cpu')
        flavor.ram = request.POST.get('ram')
        flavor.disk = request.POST.get('disk')
        flavor.save()
        return redirect(flavors_info, flavor.id)

def flavors_info(request, flavor_id):
    flavor = models.Flavor.objects.get(id=flavor_id)
    html = render('flavors_info.html', 'flavors', flavor=flavor)
    return HttpResponse(html)

def flavors_modify(request, flavor_id):
    flavor = models.Flavor.objects.get(id=flavor_id)
    flavor.cpu = request.POST.get('cpu')
    flavor.ram = request.POST.get('ram')
    flavor.disk = request.POST.get('disk')
    flavor.save()
    return redirect(flavors_info, flavor.id)

def flavors_delete(request, flavor_id):
    flavor = models.Flavor.objects.get(id=flavor_id)
    flavor.delete()
    return redirect(flavors_list)


def images_list(request):
    images = models.Image.objects.order_by('id')
    html = render('images_list.html', 'images', images=images)
    return HttpResponse(html)

def images_register(request):
    if request.method == 'GET':
        html = render('images_register.html', 'images')
        return HttpResponse(html)
    elif request.method == 'POST':
        image = models.Image()
        image.state = 'ACTIVE'
        image.name = request.POST.get('name')
        owner_id = request.POST.get('owner') or None
        image.owner = owner_id and models.SynnefoUser.objects.get(id=owner_id)
        image.backend_id = request.POST.get('backend')
        image.public = True if request.POST.get('public') else False
        image.save()
        return redirect(images_info, image.id)

def images_info(request, image_id):
    image = models.Image.objects.get(id=image_id)
    states = [x[0] for x in models.Image.IMAGE_STATES]
    if not image.state:
        states = [''] + states
    formats = [x[0] for x in models.Image.FORMATS]
    if not image.format:
        formats = [''] + formats
    html = render('images_info.html', 'images',
                    image=image, states=states, formats=formats)
    return HttpResponse(html)

def images_modify(request, image_id):
    image = models.Image.objects.get(id=image_id)
    image.name = request.POST.get('name')
    image.state = request.POST.get('state')
    owner_id = request.POST.get('owner') or None
    image.owner = owner_id and models.SynnefoUser.objects.get(id=owner_id)
    vm_id = request.POST.get('sourcevm') or None
    image.sourcevm = vm_id and models.VirtualMachine.objects.get(id=vm_id)
    image.backend_id = request.POST.get('backend')
    image.format = request.POST.get('format')
    image.public = True if request.POST.get('public') else False
    image.save()
    return redirect(images_info, image.id)


def servers_list(request):
    vms = models.VirtualMachine.objects.order_by('id')
    html = render('servers_list.html', 'servers', vms=vms)
    return HttpResponse(html)


def users_list(request):
    users = models.SynnefoUser.objects.order_by('id')
    html = render('users_list.html', 'users', users=users)
    return HttpResponse(html)

def users_invite(request):
    if request.method == 'GET':
        html = render('users_invite.html', 'users')
        return HttpResponse(html)
    elif request.method == 'POST':
        inviter_id = request.POST.get('inviter')
        realname = request.POST.get('realname')
        uniq = request.POST.get('uniq')
        inviter = models.SynnefoUser.objects.get(id=inviter_id)
        inv = add_invitation(inviter, realname, uniq)
        send_invitation(inv)
        return redirect(users_list)

def users_info(request, user_id):
    user = models.SynnefoUser.objects.get(id=user_id)
    types = [x[0] for x in models.SynnefoUser.ACCOUNT_TYPE]
    if not user.type:
        types = [''] + types
    html = render('users_info.html', 'users', user=user, types=types)
    return HttpResponse(html)

def users_modify(request, user_id):
    user = models.SynnefoUser.objects.get(id=user_id)
    user.name = request.POST.get('name')
    user.realname = request.POST.get('realname')
    user.uniq = request.POST.get('uniq')
    user.credit = int(request.POST.get('credit'))
    user.type = request.POST.get('type')
    invitations = request.POST.get('invitations')
    user.max_invitations = int(invitations) if invitations else None
    user.save()
    return redirect(users_info, user.id)
