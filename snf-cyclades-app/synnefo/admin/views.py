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

from functools import wraps

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string

from synnefo.db import models
from synnefo.invitations.invitations import add_invitation, send_invitation
from synnefo.logic import backend, users
from synnefo.util.log import getLogger


log = getLogger('synnefo.admin')


def render(template, tab, **kwargs):
    kwargs.setdefault('tab', tab)
    return render_to_string(template, kwargs)


def requires_admin(func):
    @wraps(func)
    def wrapper(request, *args):
        if not request.user or request.user.type != 'ADMIN':
            return HttpResponse('Forbidden', status=403)
        return func(request, *args)
    return wrapper


def get_filters(request, session_key, all_filters, default=None):
    if default is None:
        default = all_filters
    filters = request.session.get(session_key, default)
    filter = request.GET.get('toggle_filter')
    if filter:
        if filter in filters:
            filters.remove(filter)
        elif filter in all_filters:
            filters.add(filter)
        request.session[session_key] = filters
    return filters


@requires_admin
def index(request):
    stats = {}
    stats['users'] = models.SynnefoUser.objects.count()
    stats['images'] = models.Image.objects.exclude(state='DELETED').count()
    stats['flavors'] = models.Flavor.objects.count()
    stats['vms'] = models.VirtualMachine.objects.filter(deleted=False).count()
    stats['networks'] = models.Network.objects.exclude(state='DELETED').count()
    stats['invitations'] = models.Invitations.objects.count()

    stats['ganeti_instances'] = len(backend.get_ganeti_instances())
    stats['ganeti_nodes'] = len(backend.get_ganeti_nodes())
    stats['ganeti_jobs'] = len(backend.get_ganeti_jobs())

    images = []
    for image in models.Image.objects.exclude(state='DELETED'):
        vms = models.VirtualMachine.objects.filter(imageid=image.id)
        count = vms.filter(deleted=False).count()
        images.append((count, image.name))
    images.sort(reverse=True)

    html = render('index.html', 'home', stats=stats, images=images)
    return HttpResponse(html)


@requires_admin
def flavors_list(request):
    all_states = set(['DELETED'])
    default = set()
    filters = get_filters(request, 'flavors_filters', all_states, default)
    
    flavors = models.Flavor.objects.all()
    if 'DELETED' not in filters:
        flavors = flavors.exclude(deleted=True)
    
    html = render('flavors_list.html', 'flavors',
                    flavors=flavors,
                    all_states=sorted(all_states),
                    filters=filters)
    return HttpResponse(html)


@requires_admin
def flavors_create(request):
    if request.method == 'GET':
        html = render('flavors_create.html', 'flavors')
        return HttpResponse(html)
    if request.method == 'POST':
        flavor = models.Flavor()
        flavor.cpu = int(request.POST.get('cpu'))
        flavor.ram = int(request.POST.get('ram'))
        flavor.disk = int(request.POST.get('disk'))
        flavor.save()
        log.info('User %s created Flavor %s', request.user.name, flavor.name)
        return redirect(flavors_info, flavor.id)


@requires_admin
def flavors_info(request, flavor_id):
    flavor = models.Flavor.objects.get(id=flavor_id)
    html = render('flavors_info.html', 'flavors',
                    flavor=flavor,
                    disk_templates=settings.GANETI_DISK_TEMPLATES)
    return HttpResponse(html)


@requires_admin
def flavors_modify(request, flavor_id):
    flavor = models.Flavor.objects.get(id=flavor_id)
    flavor.cpu = int(request.POST.get('cpu'))
    flavor.ram = int(request.POST.get('ram'))
    flavor.disk = int(request.POST.get('disk'))
    flavor.disk_template = request.POST.get('disk_template')
    flavor.deleted = True if request.POST.get('deleted') else False
    flavor.save()
    log.info('User %s modified Flavor %s', request.user.name, flavor.name)
    return redirect(flavors_info, flavor.id)


@requires_admin
def flavors_delete(request, flavor_id):
    flavor = models.Flavor.objects.get(id=flavor_id)
    flavor.delete()
    log.info('User %s deleted Flavor %s', request.user.name, flavor.name)
    return redirect(flavors_list)


@requires_admin
def images_list(request):
    all_states = set(x[0] for x in models.Image.IMAGE_STATES)
    default = all_states - set(['DELETED'])
    filters = get_filters(request, 'images_filters', all_states, default)
    
    images = models.Image.objects.all()
    for state in all_states - filters:
        images = images.exclude(state=state)
    
    html = render('images_list.html', 'images',
                    images=images.order_by('id'),
                    all_states=sorted(all_states),
                    filters=filters)
    return HttpResponse(html)


@requires_admin
def images_register(request):
    if request.method == 'GET':
        formats = [x[0] for x in models.Image.FORMATS]
        html = render('images_register.html', 'images', formats=formats)
        return HttpResponse(html)
    elif request.method == 'POST':
        image = models.Image()
        image.state = 'ACTIVE'
        image.name = request.POST.get('name')
        owner_id = request.POST.get('owner') or None
        image.owner = owner_id and models.SynnefoUser.objects.get(id=owner_id)
        image.backend_id = request.POST.get('backend')
        image.format = request.POST.get('format')
        image.public = True if request.POST.get('public') else False
        image.save()
        log.info('User %s registered Image %s', request.user.name, image.name)
        return redirect(images_info, image.id)


@requires_admin
def images_info(request, image_id):
    image = models.Image.objects.get(id=image_id)
    states = [x[0] for x in models.Image.IMAGE_STATES]
    if not image.state:
        states = [''] + states
    formats = [x[0] for x in models.Image.FORMATS]
    if not image.format:
        formats = [''] + formats
    
    metadata = image.metadata.order_by('meta_key')
    html = render('images_info.html', 'images',
                    image=image,
                    states=states,
                    formats=formats,
                    metadata=metadata)
    return HttpResponse(html)


@requires_admin
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
    
    keys = request.POST.getlist('key')
    vals = request.POST.getlist('value')
    meta = dict(zip(keys, vals))
    image.metadata.all().delete()
    for key, val in meta.items():
        if key:
            image.metadata.create(meta_key=key, meta_value=val)
    
    log.info('User %s modified Image %s', request.user.name, image.name)

    return redirect(images_info, image.id)


@requires_admin
def servers_list(request):
    all_states = set(x[0] for x in models.VirtualMachine.OPER_STATES)
    default = all_states - set(['DESTROYED'])
    filters = get_filters(request, 'servers_filters', all_states, default)
    
    servers = models.VirtualMachine.objects.all()
    for state in all_states - filters:
        servers = servers.exclude(operstate=state)
    
    html = render('servers_list.html', 'servers',
                    servers=servers.order_by('id'),
                    all_states=sorted(all_states),
                    filters=filters)
    return HttpResponse(html)


@requires_admin
def users_list(request):
    all_states = set(x[0] for x in models.SynnefoUser.ACCOUNT_STATE)
    default = all_states - set(['DELETED'])
    filters = get_filters(request, 'users_filters', all_states, default)
    
    users = models.SynnefoUser.objects.all()
    for state in all_states - filters:
        users = users.exclude(state=state)
    
    html = render('users_list.html', 'users',
                    users=users.order_by('id'),
                    all_states=sorted(all_states),
                    filters=filters)
    return HttpResponse(html)


@requires_admin
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
        log.info('User %s sent Invitation to %s as %s', request.user.name,
                    uniq, inviter.name)
        return redirect(users_list)


@requires_admin
def users_info(request, user_id):
    user = models.SynnefoUser.objects.get(id=user_id)
    types = [x[0] for x in models.SynnefoUser.ACCOUNT_TYPE]
    if not user.type:
        types = [''] + types
    states = [x[0] for x in models.SynnefoUser.ACCOUNT_STATE]
    html = render('users_info.html', 'users',
                    user=user, types=types, states=states)
    return HttpResponse(html)


@requires_admin
def users_modify(request, user_id):
    user = models.SynnefoUser.objects.get(id=user_id)
    user.name = request.POST.get('name')
    user.realname = request.POST.get('realname')
    user.uniq = request.POST.get('uniq')
    user.credit = int(request.POST.get('credit'))
    user.type = request.POST.get('type')
    user.state = request.POST.get('state')
    invitations = request.POST.get('invitations')
    user.max_invitations = int(invitations) if invitations else None
    user.save()
    log.info('User %s modified User %s', request.user.name, user.name)
    return redirect(users_info, user.id)


@requires_admin
def users_delete(request, user_id):
    user = models.SynnefoUser.objects.get(id=user_id)
    users.delete_user(user)
    log.info('User %s deleted User %s', request.user.name, user.name)
    return redirect(users_list)


@requires_admin
def invitations_list(request):
    invitations = models.Invitations.objects.order_by('id')
    html = render('invitations_list.html', 'invitations',
                     invitations=invitations)
    return HttpResponse(html)


@requires_admin
def invitations_resend(request, invitation_id):
    invitation = models.Invitations.objects.get(id=invitation_id)
    send_invitation(invitation)
    log.info('User %s resent Invitations from %s to %s', request.user.name,
                invitation.source.name, invitation.target.name)
    return redirect(invitations_list)
