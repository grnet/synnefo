from functools import wraps

from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string

from synnefo.db import models
from synnefo.invitations.invitations import add_invitation, send_invitation
from synnefo.logic import backend, log, users


_log = log.get_logger('synnefo.admin')


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
        vms = models.VirtualMachine.objects.filter(sourceimage=image)
        count = vms.filter(deleted=False).count()
        images.append((count, image.name))
    images.sort(reverse=True)

    html = render('index.html', 'home', stats=stats, images=images)
    return HttpResponse(html)


@requires_admin
def flavors_list(request):
    flavors = models.Flavor.objects.order_by('id')
    html = render('flavors_list.html', 'flavors', flavors=flavors)
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
        _log.info('User %s created Flavor %s', request.user.name, flavor.name)
        return redirect(flavors_info, flavor.id)


@requires_admin
def flavors_info(request, flavor_id):
    flavor = models.Flavor.objects.get(id=flavor_id)
    html = render('flavors_info.html', 'flavors', flavor=flavor)
    return HttpResponse(html)


@requires_admin
def flavors_modify(request, flavor_id):
    flavor = models.Flavor.objects.get(id=flavor_id)
    flavor.cpu = int(request.POST.get('cpu'))
    flavor.ram = int(request.POST.get('ram'))
    flavor.disk = int(request.POST.get('disk'))
    flavor.save()
    _log.info('User %s modified Flavor %s', request.user.name, flavor.name)
    return redirect(flavors_info, flavor.id)


@requires_admin
def flavors_delete(request, flavor_id):
    flavor = models.Flavor.objects.get(id=flavor_id)
    flavor.delete()
    _log.info('User %s deleted Flavor %s', request.user.name, flavor.name)
    return redirect(flavors_list)


@requires_admin
def images_list(request):
    images = models.Image.objects.order_by('id')
    html = render('images_list.html', 'images', images=images)
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
        _log.info('User %s registered Image %s', request.user.name, image.name)
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
    
    _log.info('User %s modified Image %s', request.user.name, image.name)

    return redirect(images_info, image.id)


@requires_admin
def servers_list(request):
    vms = models.VirtualMachine.objects.order_by('id')
    html = render('servers_list.html', 'servers', vms=vms)
    return HttpResponse(html)


@requires_admin
def users_list(request):
    users = models.SynnefoUser.objects.order_by('id')
    html = render('users_list.html', 'users', users=users)
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
        _log.info('User %s sent Invitation to %s as %s', request.user.name,
                    uniq, inviter.name)
        return redirect(users_list)


@requires_admin
def users_info(request, user_id):
    user = models.SynnefoUser.objects.get(id=user_id)
    types = [x[0] for x in models.SynnefoUser.ACCOUNT_TYPE]
    if not user.type:
        types = [''] + types
    html = render('users_info.html', 'users', user=user, types=types)
    return HttpResponse(html)


@requires_admin
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
    _log.info('User %s modified User %s', request.user.name, user.name)
    return redirect(users_info, user.id)


@requires_admin
def users_delete(request, user_id):
    user = models.SynnefoUser.objects.get(id=user_id)
    users.delete_user(user)
    _log.info('User %s deleted User %s', request.user.name, user.name)
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
    _log.info('User %s resent Invitations from %s to %s', request.user.name,
                invitation.source.name, invitation.target.name)
    return redirect(invitations_list)
