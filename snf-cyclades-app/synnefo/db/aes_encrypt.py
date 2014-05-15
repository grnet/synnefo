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
