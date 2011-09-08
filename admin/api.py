import json

from django.core.urlresolvers import reverse
from django.http import HttpResponse

from synnefo.admin.views import requires_admin
from synnefo.db import models


@requires_admin
def servers_info(request, server_id):
    server = models.VirtualMachine.objects.get(id=server_id)
    reply = {
    	'name': server.name,
    	'ref': '#'}
    return HttpResponse(json.dumps(reply), content_type='application/json')


@requires_admin
def users_info(request, user_id):
    user = models.SynnefoUser.objects.get(id=user_id)
    reply = {
    	'name': user.name,
    	'ref': reverse('synnefo.admin.views.users_info', args=(user_id,))}
    return HttpResponse(json.dumps(reply), content_type='application/json')
