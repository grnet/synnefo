from django.conf.urls.defaults import patterns
from django.views.generic import list_detail

from synnefo.db.models import Invitations

all_invitations = {
    "queryset" : Invitations.objects.filter(source = request.user),
    "template_name" : "invitations.html"
}

urlpatterns = patterns('',
    (r'^$', list_detail.object_list, all_invitations)
)
