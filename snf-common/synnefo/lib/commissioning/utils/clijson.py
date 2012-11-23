#!/usr/bin/env python

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

