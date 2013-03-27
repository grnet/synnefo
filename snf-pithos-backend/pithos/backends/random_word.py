# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

DEFAULT_ALPHABET = ('0123456789'
                    'abcdefghijklmnopqrstuvwxyz'
                    'ABCDEFGHIJKLMNOPQRSTUVWXYZ')
DEFAULT_MIN_LENGTH = 8

from  random import randrange
from math import log

def get_random_word(length=DEFAULT_MIN_LENGTH, alphabet=DEFAULT_ALPHABET):
    alphabet_length = len(alphabet)
    word = ''.join(alphabet[randrange(alphabet_length)]
        for _ in xrange(length))
    return word

def encode_serial(serial, alphabet=DEFAULT_ALPHABET):
    i = 0
    base = len(alphabet)
    quotient = int(serial)
    digits = []
    append = digits.append
    while quotient > 0:
        quotient, remainder = divmod(quotient, base)
        append(alphabet[remainder])
    word = ''.join(reversed(digits))
    return word

def get_word(serial, length=DEFAULT_MIN_LENGTH, alphabet=DEFAULT_ALPHABET):
    word = encode_serial(serial, alphabet)
    word += get_random_word(length, alphabet)
    return word
