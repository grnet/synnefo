from django.conf.urls.defaults import patterns
from django.views.generic import list_detail

from synnefo.db.models import SynnefoUser

from synnefo.invitations.views import inv_demux

all_invitations = {
    "queryset" : Invitation.objects.all(),
}

urlpatterns = patterns('',
    (r'^$', list_detail.object_list, all_invitations)
)
