#!/usr/bin/env python

from re import split as re_split

keywords = set(['true', 'false', 'null'])


def quote(token, is_dict):
    if not token[0].isalpha():
        return token

    k, sep, v = token.partition('=')
    if not sep or not v.strip('='):
        k, sep, v = token.partition(':')
    if not k:
        k = '""'

    if not sep:
        if token not in keywords and token[0] not in '{["\'':
            return '"' + token + '"'
        return token

    k = '"' + k + '"'
    is_dict.add(1)

    if not v:
        v = '""'

    return k + ':' + quote(v, is_dict)


def clijson(argv):
    s = ','.join(argv)
    tokens = re_split('([^\w @_.-]+)', s)
    tokens = argv
    is_dict = set()

    strlist = []
    append = strlist.append
    dictionary = 0
    token_join = None

    for t in tokens:
        t = t.strip()
        if not t:
            continue

        if token_join:
            t = token_join + t
            token_join = None

        t = quote(t, is_dict)
        append(t)

    if not strlist:
        s = 'null'
    elif strlist[0][0] not in '{[':
        if is_dict:
            s = '{' + ','.join(strlist) + '}'
        else:
            s = '[' + ','.join(strlist) + ']'

    return s


if __name__ == '__main__':
    from sys import argv

    print clijson(argv[1:])

