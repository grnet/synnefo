#!/usr/bin/env python

# Copyright 2012 GRNET S.A. All rights reserved.
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

import re

keywords = set(['true', 'false', 'null'])
unquoted = set('{}[]"\'0123456789')
name_matcher = re.compile('^[\w @_.+-]+$', re.UNICODE)

def is_name(token):
    if name_matcher.match(token):
        return 1
    return 0

def quote(token, is_dict):
    if not token:
        return '""'

    if not is_name(token[0]):
        comma = ', ' if token[-1] not in '{[' else ''
        return token + comma

    k, sep, v = token.partition('=')
    if not sep or not v.strip('='):
        k, sep, v = token.partition(':')

    if not sep:
        if is_name(token) and token not in keywords:
            token = '"' + token + '"'

        comma = ', ' if token[-1] not in '{[' else ''
        return token + comma

    k = '"' + k + '"'
    is_dict.add(1)

    if not v:
        v = '""'
    else:
        if v.isalnum() and not v.isdigit() and v not in keywords:
            v = '"' + v + '"'

    comma = ', ' if v[-1] not in '{[' else ''
    return k + ':' + v + comma


def clijson(argv):
    tokens = argv
    is_dict = set()

    strlist = []
    append = strlist.append
    dictionary = 0
    token_join = None

    for t in tokens:
        t = t.strip()

        if strlist and t and t in '}]':
            strlist[-1] = strlist[-1].rstrip(', ')

        if token_join:
            t = token_join + t
            token_join = None
        elif t.endswith(':'):
            token_join = t
            continue

        t = quote(t, is_dict)
        append(t)

    if not strlist:
        return 'null'

    if strlist[0][0] not in '{[':
        strlist[-1] = strlist[-1].rstrip(', ')
        o, e = '{}' if is_dict else '[]'
        strlist = [o] + strlist + [e]

    if strlist[-1][-1] in ']}':
        strlist[-1] = strlist[-1].rstrip(',')
    return ''.join(strlist)


if __name__ == '__main__':
    from sys import argv

    print clijson(argv[1:])

