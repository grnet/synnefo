#
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

from django import http
from django.utils import simplejson as json
from django.conf import settings

from synnefo.ui.userdata import rest
from synnefo.ui.userdata.models import PublicKeyPair
from synnefo.ui.userdata.util import exportKey
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

    get_user(request, settings.ASTAKOS_BASE_URL)

    if request.method != "POST":
        return http.HttpResponseNotAllowed(["POST"])

    if not SUPPORT_GENERATE_KEYS:
        raise Exception("Application does not support ssh keys generation")

    if PublicKeyPair.user_limit_exceeded(request.user):
        raise http.HttpResponseServerError("SSH keys limit exceeded")

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
