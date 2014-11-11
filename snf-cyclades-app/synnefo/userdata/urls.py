#
# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls import patterns, url

from synnefo.userdata import views
from django.http import Http404


def index(request):
    raise Http404

urlpatterns = patterns(
    '',
    url(r'^$', index, name='ui_userdata'),
    url(r'^keys$',
        views.PublicKeyPairCollectionView.as_view('ui_keys_resource'),
        name='ui_keys_collection'),
    url(r'^keys/(?P<id>\d+)',
        views.PublicKeyPairResourceView.as_view('ui_keys_resource'),
        name="ui_keys_resource"),
    url(r'keys/generate', views.generate_key_pair,
        name="ui_generate_public_key"),
    url(r'keys/download', views.download_private_key,
        name="ui_download_public_key")
)
