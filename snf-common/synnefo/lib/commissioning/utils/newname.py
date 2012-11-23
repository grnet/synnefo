
from time import time

_counter = 0

def newname(prefix):
    global _counter;
    _counter += 1
    ident = id(locals())
    nonce = int(time() * 1000) + _counter
    return "%s%x%x" % (prefix, ident, nonce)

