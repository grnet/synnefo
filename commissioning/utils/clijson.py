#!/usr/bin/env python

from re import split as re_split

keywords = set(['true', 'false', 'null'])

def clijson(argv):
    s = ','.join(argv)
    tokens = re_split('([^\w@_.-]+)', s)

    strlist = ['{']
    append = strlist.append
    quoting = 0

    for t in tokens:
        t = t.strip()
        if not t:
            continue

        if quoting:
            append(t)
            continue

        count = t.count('"')
        quoting = (quoting + count) & 1

        if t.startswith('"'):
            continue

        if not t[0].isalpha():
            if '=' in t:
                t = t.replace('=', ':')
                quote = 1
        elif t not in keywords:
            t = '"' + t + '"'

        append(t)

    append('}')
    z = len(strlist)
    if z <= 2:
        strlist = ['null']
    elif len(argv) < 2 and strlist[1][0] in '{[' or strlist[1] in keywords:
        strlist[0] = ''
        strlist[-1] = ''

    return ''.join(strlist)


if __name__ == '__main__':
    from sys import argv

    print clijson(argv[1:])

