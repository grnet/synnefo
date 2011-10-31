from django import http
from django.template import RequestContext, loader
from django.utils import simplejson as json
from django.conf import settings

from synnefo.ui.userdata import rest
from synnefo.ui.userdata.models import PublicKeyPair


SUPPORT_GENERATE_KEYS = True
try:
    import M2Crypto as M2C
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
SSH_KEY_EXPONENT = getattr(settings, 'USERDATA_SSH_KEY_EXPONENT', 65537)
def generate_key_pair(request):
    """
    Response to generate private/public RSA key pair
    """
    if not SUPPORT_GENERATE_KEYS:
        raise Exception("Application does not support ssh keys generation")

    if PublicKeyPair.user_limit_exceeded(request.user):
        raise http.HttpResponseServerError("SSH keys limit exceeded");


    # generate RSA key
    key = M2C.RSA.gen_key(SSH_KEY_LENGTH, SSH_KEY_EXPONENT, lambda x: "");

    # get PEM string
    pem_buffer = M2C.BIO.MemoryBuffer()
    M2C.m2.rsa_write_key_no_cipher(key.rsa, pem_buffer._ptr(), lambda : "")
    pem = pem_buffer.getvalue()

    # generate public content
    public = "ssh-rsa %s" % base64.b64encode('\x00\x00\x00\x07ssh-rsa%s%s' % (key.pub()[0], key.pub()[1]))

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
