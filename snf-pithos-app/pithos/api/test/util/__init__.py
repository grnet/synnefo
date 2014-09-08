#!/usr/bin/env python
#coding=utf8

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

import re
import hashlib
import random
import string

from binascii import hexlify
from StringIO import StringIO

from pithos.api import settings as pithos_settings


def is_date(date):
    __D = r'(?P<day>\d{2})'
    __D2 = r'(?P<day>[ \d]\d)'
    __M = r'(?P<mon>\w{3})'
    __Y = r'(?P<year>\d{4})'
    __Y2 = r'(?P<year>\d{2})'
    __T = r'(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})'
    RFC1123_DATE = re.compile(r'^\w{3}, %s %s %s %s GMT$' % (
        __D, __M, __Y, __T))
    RFC850_DATE = re.compile(r'^\w{6,9}, %s-%s-%s %s GMT$' % (
        __D, __M, __Y2, __T))
    ASCTIME_DATE = re.compile(r'^\w{3} %s %s %s %s$' % (
        __M, __D2, __T, __Y))
    for regex in RFC1123_DATE, RFC850_DATE, ASCTIME_DATE:
        m = regex.match(date)
        if m is not None:
            return True
    return False


def strnextling(prefix):
    """Return the first unicode string
       greater than but not starting with given prefix.
       strnextling('hello') -> 'hellp'
    """
    if not prefix:
        ## all strings start with the null string,
        ## therefore we have to approximate strnextling('')
        ## with the last unicode character supported by python
        ## 0x10ffff for wide (32-bit unicode) python builds
        ## 0x00ffff for narrow (16-bit unicode) python builds
        ## We will not autodetect. 0xffff is safe enough.
        return unichr(0xffff)
    s = prefix[:-1]
    c = ord(prefix[-1])
    if c >= 0xffff:
        raise RuntimeError
    s += unichr(c + 1)
    return s


def get_random_data(length=None):
    length = length or random.randint(
        pithos_settings.BACKEND_BLOCK_SIZE,
        2 * pithos_settings.BACKEND_BLOCK_SIZE)
    return "".join([random.choice(string.letters) for i in xrange(length)])


def get_random_name(length=8):
    return get_random_data(length)


def md5_hash(data):
    md5 = hashlib.md5()
    md5.update(data)
    return md5.hexdigest().lower()


def file_read_iterator(fp, size=1024):
    while True:
        data = fp.read(size)
        if not data:
            break
        yield data


class HashMap(list):

    def __init__(self, blocksize, blockhash):
        super(HashMap, self).__init__()
        self.blocksize = blocksize
        self.blockhash = blockhash

    def _hash_raw(self, v):
        h = hashlib.new(self.blockhash)
        h.update(v)
        return h.digest()

    def _hash_block(self, v):
        return self._hash_raw(v.rstrip('\x00'))

    def hash(self):
        if len(self) == 0:
            return self._hash_raw('')
        if len(self) == 1:
            return self.__getitem__(0)

        h = list(self)
        s = 2
        while s < len(h):
            s = s * 2
        h += [('\x00' * len(h[0]))] * (s - len(h))
        while len(h) > 1:
            h = [self._hash_raw(h[x] + h[x + 1]) for x in range(0, len(h), 2)]
        return h[0]

    def load(self, data):
        self.size = 0
        fp = StringIO(data)
        for block in file_read_iterator(fp, self.blocksize):
            self.append(self._hash_block(block))
            self.size += len(block)


def merkle(data, blocksize, blockhash):
    hashes = HashMap(blocksize, blockhash)
    hashes.load(data)
    return hexlify(hashes.hash())
