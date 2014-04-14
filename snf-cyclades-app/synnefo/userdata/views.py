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

from django import http
from django.utils import simplejson as json
from django.conf import settings

from synnefo.userdata import rest
from synnefo.userdata.models import PublicKeyPair
from synnefo.userdata.util import exportKey
from snf_django.lib.astakos import get_user

SUPPORT_GENERATE_KEYS = True
try:
    from paramiko import rsakey
    from paramiko.message import Message
except ImportError, e:
    SUPPORT_GENERATE_KEYS = False

import base64


class PublicKeyPairResourceView(rest.UserResourceView):
    model = PublicKeyPair
    exclude_fields = ["user"]


class PublicKeyPairCollectionView(rest.UserCollectionView):
    model = PublicKeyPair
    exclude_fields = ["user"]


SSH_KEY_LENGTH = getattr(settings, 'USERDATA_SSH_KEY_LENGTH', 2048)


def generate_key_pair(request):
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

    # generate RSA key
    from Crypto import Random
    Random.atfork()

    key = rsakey.RSA.generate(SSH_KEY_LENGTH)

    # get PEM string
    pem = exportKey(key, 'PEM')

    public_data = Message()
    public_data.add_string('ssh-rsa')
    public_data.add_mpint(key.key.e)
    public_data.add_mpint(key.key.n)

    # generate public content
    public = str("ssh-rsa %s" % base64.b64encode(str(public_data)))

    data = {'private': pem, 'public': public}
    return http.HttpResponse(json.dumps(data), mimetype="application/json")


def download_private_key(request):
    """
    Return key contents
    """
    data = request.POST.get("data")
    name = request.POST.get("name", "key")

    response = http.HttpResponse(mimetype='application/x-pem-key')
    response['Content-Disposition'] = 'attachment; filename=%s' % name
    response.write(data)
    return response
