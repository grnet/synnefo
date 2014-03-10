# Copyright 2012, 2013 GRNET S.A. All rights reserved.
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

from binascii import b2a_base64, a2b_base64
from Crypto.Cipher import AES
from Crypto import Random
from random import choice
from string import letters, digits
from synnefo.settings import SECRET_ENCRYPTION_KEY


DB_ENCRYPTED_FIELD_PREFIX = 'encrypted'
SALT_LEN = 8


def _pad_secret(secret, blocksize=32, padding='}'):
    len_secret = len(secret)
    if len_secret > 32:
        raise ValueError('Encryption key must be smaller than 32 bytes')
    if not len_secret in (16, 24, 32):
        return secret + (blocksize - len(secret)) * padding
    return secret


def encrypt(s, iv):
    obj = AES.new(_pad_secret(SECRET_ENCRYPTION_KEY), AES.MODE_CFB, iv)
    return obj.encrypt(s)


def decrypt(s, iv):
    obj = AES.new(_pad_secret(SECRET_ENCRYPTION_KEY), AES.MODE_CFB, iv)
    return obj.decrypt(s)


def encrypt_db_charfield(plaintext):
    if not plaintext:
        return plaintext
    salt = "".join([choice(letters + digits) for i in xrange(SALT_LEN)])

    iv = Random.get_random_bytes(16)
    plaintext = "%s%s" % (salt, plaintext)
    # Encrypt and convert to binary
    ciphertext = b2a_base64(encrypt(plaintext, iv))
    iv = b2a_base64(iv)
    # Append prefix,salt and return encoded value
    final = '%s:%s:%s$%s' % (DB_ENCRYPTED_FIELD_PREFIX, iv, salt, ciphertext)
    return final.encode('utf8')


def decrypt_db_charfield(ciphertext):
    if not ciphertext:
        return ciphertext
    has_prefix = ciphertext.startswith(DB_ENCRYPTED_FIELD_PREFIX + ':')
    if not has_prefix:  # Non-encoded value
        return ciphertext
    else:
        _, iv, ciphertext = ciphertext.split(':')

    pure_salt, encrypted = ciphertext.split('$')
    iv = a2b_base64(iv)

    plaintext = decrypt(a2b_base64(encrypted), iv)

    salt = plaintext[:SALT_LEN]
    plaintext = plaintext[SALT_LEN:]

    if salt != pure_salt:
        # Cannot decrtypt password
        raise CorruptedPassword("Cannot decrypt password. Check the key")
    else:
        return plaintext


class CorruptedPassword(Exception):
    pass
