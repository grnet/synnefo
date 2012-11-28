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

try:
    from collections import OrderedDict
except ImportError:
    from .ordereddict import OrderedDict
from itertools import chain
from cStringIO import StringIO

ARGMAP_MAGIC = '[=ARGMAP=]'

class arguments(object):
    __slots__ = ('args', 'kw')

    def __init__(self, *args, **kwargs):
        self.args = list(args)
        kw = OrderedDict()
        kwitems = kw.pop('kwitems', None)
        if kwitems is not None:
            kw.update(kwitems)
        kw.update(kwargs)
        self.kw = kw

    def __str__(self):
        return str(self.args) + '+' + str(self.kw)

    def __repr__(self):
        return repr(self.args) + '+' + repr(self.kw)

    def __getitem__(self, key):
        if (isinstance(key, int)
            or isinstance(key, long)
            or isinstance(key, slice)):
                return self.args[key]
        else:
            return self.kw[key]

    def __setitem__(self, key, value):
        if (isinstance(key, int)
            or isinstance(key, long)
            or isinstance(key, slice)):
                self.args[key] = value
        else:
            self.kw[key] = value

    def __delitem__(self, key):
        if (isinstance(key, int)
            or isinstance(key, long)
            or isinstance(key, slice)):
                del self.args[key]
        else:
                del self.kw[key]

    def iteritems(self):
        for item in self.args:
            yield None, item
        for k, v in self.kw:
            yield k, v

    def items(self):
        return list(self.iteritems())

    def iterkeys(self):
        return self.kw.iterkeys()

    def keys(self):
        return self.kw.keys()

    def itervalues(self):
        return chain(self.args, self.kw.itervalues())

    def values(self):
        return list(self.itervalues)

    def append(self, value):
        self.args.append(value)


def argmap_encode(obj, output):
    if obj is None:
        output('[=null]')
        return

    if isinstance(obj, basestring):
        if not obj:
            output('""')
        if isinstance(obj, unicode):
            obj = obj.encode('utf-8')
        output('"')
        start = 0
        while 1:
            end = obj.find(start) + 1
            if end < 0:
                break
            output(obj[start:end] + '"')
            start = end
        output(obj[start:])
        output('"')
        return

    if isinstance(obj, int) or isinstance(obj, long):
        output(str(obj))
        return

    if hasattr(obj, 'iteritems'):
        output('[')
        once = 1
        for k, v in obj.iteritems():
            if once:
                once = 0
            else:
                output(' ')
            if k is not None:
                argmap_encode(k)
                output('=')
            argmap_encode(v)
        output(']')
        
    if hasattr(obj, '__iter__'):
        output('[')
        once = 1
        for item in obj:
            if once:
                once = 0
            else:
                output(' ')
            argmap_encode(item)
        output(']')

    m = "Unsupported type '%s'" % (type(obj))


def argmap_decode(inputf, s=None):
    if isinstance(inputf, str):
        inputf = StringIO(inputf).read

    if s is None:
        s = inputf(1)

    while 1:
        if not s.isspace():
            break
        s = inputf(1)

    item = ''
    if s == '"':
        s = inputf(1)
        while 1:
            if s == '"':
                s = inputf(1)
                if s != '"':
                    return item, s
            item += s
            s = inputf(1)
    elif s == '[':
        item, s = argmap_decode_args(inputf)
        return item, s
    else:
        while 1:
            item += s
            s = inputf(1)
            if s in ' =]':
                return item, s


def argmap_decode_atom(inputf):
    s = inputf(4)
    if s != 'null':
        m = "Invalid atom '%s'" % (s,)
        raise ValueError(m)
    return None, None


def argmap_decode_args(inputf):
    args = [ARGMAP_MAGIC]
    append = args.append
    s = inputf(1)
    key = None

    while 1:
        if s is None:
            s = inputf(1)

        if s == ']':
            if key is not None:
                append((None, key))
            return args, None

        if s == '=':
            if key is None:
                atom, s = argmap_decode_atom(inputf)
                append((None, atom))
            else:
                value, s = argmap_decode(inputf)
                append((key, value))
                key = None
        elif s == ' ':
            if key is not None:
                append((None, key))
                key = None
            s = inputf(1)
        elif s == '':
            m = "EOF while scanning for ']'"
            raise ValueError(m)
        else:
            if key is not None:
                append((None, key))
            key, s = argmap_decode(inputf, s=s)


def argmap_check(obj):
    if hasattr(obj, 'keys'):
        # this could cover both cases
        return ARGMAP_MAGIC in obj
    return hasattr(obj, '__len__') and len(obj) and obj[0] == ARGMAP_MAGIC

def argmap_unzip_dict(argmap):
    if not hasattr(argmap, 'keys'):
        m = "argmap unzip dict: not a dict"
        raise TypeError(m)
    if ARGMAP_MAGIC not in argmap:
        m = "argmap unzip dict: magic not found"
        raise ValueError(m)
    args = argmap.pop(None, [])
    kw = OrderedDict(argmap)
    del kw[ARGMAP_MAGIC]
    return args, kw

def argmap_unzip_list(argmap):
    if not argmap or argmap[0] != ARGMAP_MAGIC:
        m = "argmap unzip list: magic not found"
        raise ValueError(m)

    iter_argmap = iter(argmap)
    for magic in iter_argmap:
        break

    args = []
    append = args.append
    kw = OrderedDict()
    for k, v in iter_argmap:
        if k is None:
            append(v)
        else:
            kw[k] = v

    return args, kw

def argmap_unzip(argmap):
    if hasattr(argmap, 'keys'):
        return argmap_unzip_dict(argmap)
    elif hasattr(argmap, '__iter__'):
        return argmap_unzip_list(argmap)
    else:
        m = "argmap: cannot unzip type %s" % (type(argmap),)
        raise ValueError(m)

def argmap_zip_list(args, kw):
    return [ARGMAP_MAGIC] + [(None, a) for a in args] + kw.items()

def argmap_zip_dict(args, kw):
    argmap = OrderedDict()
    argmap.update(kw)
    argmap[ARGMAP_MAGIC] = ARGMAP_MAGIC
    argmap[None] = list(args) + (argmap[None] if None in argmap else [])
    return argmap

argmap_zip = argmap_zip_list

