from django import http
from django.template import RequestContext, loader
from django.utils import simplejson as json
from django.conf import settings

from synnefo.ui.userdata import rest
from synnefo.ui.userdata.models import PublicKeyPair


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
    if not SUPPORT_GENERATE_KEYS:
        raise Exception("Application does not support ssh keys generation")

    if PublicKeyPair.user_limit_exceeded(request.user):
        raise http.HttpResponseServerError("SSH keys limit exceeded");


    # generate RSA key
    key = rsakey.RSA.generate(SSH_KEY_LENGTH);

    # get PEM string
    pem = key.exportKey('PEM')

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
    response['Content-Disposition'] = 'attachment; filename=%s.pem' % name
    response.write(data)
    return response
