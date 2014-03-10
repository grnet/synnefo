# Copyright 2011, 2012, 2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.

import binascii

from synnefo.userdata.asn1 import DerObject, DerSequence

def exportKey(keyobj, format='PEM'):
    """Export the RSA key. A string is returned
    with the encoded public or the private half
    under the selected format.

    format: 'DER' (PKCS#1) or 'PEM' (RFC1421)
    """
    der = DerSequence()
    if keyobj.has_private():
        keyType = "RSA PRIVATE"
        der[:] = [ 0, keyobj.n, keyobj.e, keyobj.d, keyobj.p, keyobj.q,
        keyobj.d % (keyobj.p-1), keyobj.d % (keyobj.q-1),
        keyobj.u ]
    else:
        keyType = "PUBLIC"
        der.append('\x30\x0D\x06\x09\x2A\x86\x48\x86\xF7\x0D\x01\x01\x01\x05\x00')
        bitmap = DerObject('BIT STRING')
        derPK = DerSequence()
        derPK[:] = [ keyobj.n, keyobj.e ]
        bitmap.payload = '\x00' + derPK.encode()
        der.append(bitmap.encode())
    if format=='DER':
        return der.encode()
    if format=='PEM':
        pem = "-----BEGIN %s KEY-----\n" % keyType
        binaryKey = der.encode()
        # Each BASE64 line can take up to 64 characters (=48 bytes of data)
        chunks = [ binascii.b2a_base64(binaryKey[i:i+48]) for i in range(0, len(binaryKey), 48) ]
        pem += ''.join(chunks)
        pem += "-----END %s KEY-----" % keyType
        return pem
    return ValueError("")
