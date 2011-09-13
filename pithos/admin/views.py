from functools import wraps

from django.http import HttpResponse, HttpResponseRedirect
from django.utils.http import urlencode
from django.shortcuts import redirect
from django.template.loader import render_to_string

from pithos import settings
from pithos.aai.models import PithosUser



def render(template, tab, **kwargs):
    kwargs.setdefault('tab', tab)
    return render_to_string(template, kwargs)


def requires_admin(func):
    @wraps(func)
    def wrapper(request, *args):
        if not request.user:
            login_uri = settings.LOGIN_URL + '?' + urlencode({'next': request.build_absolute_uri()})
            return HttpResponseRedirect(login_uri)
        if not request.user_obj.is_admin:
            return HttpResponse('Forbidden', status=403)
        return func(request, *args)
    return wrapper


@requires_admin
def index(request):
    stats = {}
    stats['users'] = PithosUser.objects.count()
    html = render('index.html', 'home', stats=stats)
    return HttpResponse(html)


@requires_admin
def users_list(request):
    users = PithosUser.objects.order_by('id')
    html = render('users_list.html', 'users', users=users)
    return HttpResponse(html)


@requires_admin
def users_create(request):
    if request.method == 'GET':
        html = render('users_create.html', 'users')
        return HttpResponse(html)
    if request.method == 'POST':
        user = PithosUser()
        user.uniq = request.POST.get('uniq')
        user.realname = request.POST.get('realname')
        user.is_admin = True if request.POST.get('admin') else False
        user.affiliation = request.POST.get('affiliation')
        user.quota = int(request.POST.get('quota') or 0)
        user.auth_token = request.POST.get('auth_token')
        user.save()
        return redirect(users_info, user.id)


@requires_admin
def users_info(request, user_id):
    user = PithosUser.objects.get(id=user_id)
    html = render('users_info.html', 'users', user=user)
    return HttpResponse(html)


@requires_admin
def users_modify(request, user_id):
    user = PithosUser.objects.get(id=user_id)
    user.uniq = request.POST.get('uniq')
    user.realname = request.POST.get('realname')
    user.is_admin = True if request.POST.get('admin') else False
    user.affiliation = request.POST.get('affiliation')
    user.quota = int(request.POST.get('quota') or 0)
    user.auth_token = request.POST.get('auth_token')
    user.save()
    return redirect(users_info, user.id)


@requires_admin
def users_delete(request, user_id):
    user = PithosUser.objects.get(id=user_id)
    user.delete()
    return redirect(users_list)
