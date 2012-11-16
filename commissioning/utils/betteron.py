try:
    from collections import OrderedDict
except ImportError:
    from commissioning.utils.ordereddict import OrderedDict
from itertools import chain
from cStringIO import StringIO

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


def betteron_encode(obj, output):
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
                betteron_encode(k)
                output('=')
            betteron_encode(v)
        output(']')
        
    if hasattr(obj, '__iter__'):
        output('[')
        once = 1
        for item in obj:
            if once:
                once = 0
            else:
                output(' ')
            betteron_encode(item)
        output(']')

    m = "Unsupported type '%s'" % (type(obj))


def betteron_decode(inputf, s=None):
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
        item, s = betteron_decode_args(inputf)
        return item, s
    else:
        while 1:
            item += s
            s = inputf(1)
            if s in ' =]':
                return item, s


def betteron_decode_atom(inputf):
    s = inputf(4)
    if s != 'null':
        m = "Invalid atom '%s'" % (s,)
        raise ValueError(m)
    return None, None


def betteron_decode_args(inputf):
    args = []
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
                atom, s = betteron_decode_atom(inputf)
                append((None, atom))
            else:
                value, s = betteron_decode(inputf)
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
            key, s = betteron_decode(inputf, s=s)

