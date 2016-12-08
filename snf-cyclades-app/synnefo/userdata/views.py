#
# Copyright (C) 2010-2016 GRNET S.A.
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

from django import http
import json
from django.conf import settings

from synnefo.userdata import rest
from synnefo.userdata.models import PublicKeyPair
from synnefo.userdata.util import exportKey, generate_keypair, SUPPORT_GENERATE_KEYS
from snf_django.lib.astakos import get_user


class PublicKeyPairResourceView(rest.UserResourceView):
    model = PublicKeyPair
    exclude_fields = ["user", "deleted", "deleted_at",
                      "updated_at", "created_at", "type"]


class PublicKeyPairCollectionView(rest.UserCollectionView):
    model = PublicKeyPair
    exclude_fields = ["user", "deleted", "deleted_at",
                      "updated_at", "created_at", "type"]


def create_new_keypair(request):
    """
    Response to generate private/public RSA key pair
    """

    get_user(request, settings.ASTAKOS_AUTH_URL)

    if request.method != "POST":
        return http.HttpResponseNotAllowed(["POST"])

    if not SUPPORT_GENERATE_KEYS:
        raise Exception("Application does not support ssh keys generation")

    if PublicKeyPair.user_limit_exceeded(request.user_uniq):
        return http.HttpResponseServerError("SSH keys limit exceeded")

    data = generate_keypair()
    return http.HttpResponse(json.dumps(data), content_type="application/json")


def download_private_key(request):
    """
    Return key contents
    """
    data = request.POST.get("data")
    name = request.POST.get("name", "key")

    response = http.HttpResponse(content_type='application/x-pem-key')
    response['Content-Disposition'] = 'attachment; filename=%s' % name
    response.write(data)
    return response
