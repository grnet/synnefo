from django import http
from django.template import RequestContext, loader
from django.utils import simplejson as json
from django.conf import settings

from synnefo.userdata import rest
from synnefo.userdata.models import PublicKeyPair

from synnefo.userdata import asn1
from Crypto.PublicKey import RSA
from Crypto.Util.number import inverse

import binascii
import base64

class PublicKeyPairResourceView(rest.UserResourceView):
    model = PublicKeyPair
    exclude_fields = ["user"]

class PublicKeyPairCollectionView(rest.UserCollectionView):
    model = PublicKeyPair
    exclude_fields = ["user"]

SSH_KEY_LENGTH = getattr(settings, 'UI_SSH_KEY_LENGTH', 1024)
def generate_key_pair(request):
    """
    Response to generate private/public RSA key pair
    """
    key = RSA.generate(SSH_KEY_LENGTH)

    # generate private content in PEM format
    seq = asn1.DerSequence()
    seq[:] = [ 0, key.n, key.e, key.d, key.p, key.q, key.d % (key.p-1), key.d % (key.q-1), inverse(key.q, key.p)]
    pem = asn1.b("-----BEGIN PRIVATE KEY-----\n")
    binaryKey = seq.encode()
    chunks = [ binascii.b2a_base64(binaryKey[i:i+48]) for i in range(0, len(binaryKey), 48) ]
    pem += asn1.b('').join(chunks)
    pem += asn1.b("-----END PRIVATE KEY-----\n")

    # generate public content
    seq = asn1.DerSequence()
    ssh_rsa = '00000007' + base64.b16encode('ssh_rsa')
    exponent = '%x' % (key.e, )
    if len(exponent) % 2:
        exponent = '0' + exponent
    ssh_rsa += '%08x' % (len(exponent) / 2, )
    ssh_rsa += exponent
    modulus = '%x' % (key.n, )
    if len(modulus) % 2:
        modulus = '0' + modulus
    if modulus[0] in '89abcdef':
        modulus = '00' + modulus
    ssh_rsa += '%08x' % (len(modulus) / 2, )
    ssh_rsa += modulus
    public = 'ssh-rsa %s' % (base64.b64encode(base64.b16decode(ssh_rsa.upper())),)

    print pem
    print
    print
    print public

    data = {'private': pem, 'public': public}
    return http.HttpResponse(json.dumps(data), mimetype="application/json")
