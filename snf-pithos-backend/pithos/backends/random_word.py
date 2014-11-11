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

import random

getrandbits = random.SystemRandom().getrandbits

DEFAULT_ALPHABET = ("0123456789"
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    "abcdefghijklmnopqrstuvwxyz")


def get_random_word(length, alphabet=DEFAULT_ALPHABET):
    remainder = getrandbits(length * 8)
    return encode_word(remainder, alphabet=alphabet)


def encode_word(number, alphabet=DEFAULT_ALPHABET):
    base = len(alphabet)
    digits = []
    append = digits.append
    quotient = number
    while True:
        quotient, remainder = divmod(quotient, base)
        append(alphabet[remainder])
        if quotient <= 0:
            break

    return ''.join(digits)
