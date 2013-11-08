# Copyright 2012, 2013 GRNET S.A. All rights reserved.
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

import copy


def dict_merge(a, b):
    """
    http://www.xormedia.com/recursively-merge-dictionaries-in-python/
    """
    if not isinstance(b, dict):
        return b
    result = copy.deepcopy(a)
    for k, v in b.iteritems():
        if k in result and isinstance(result[k], dict):
                result[k] = dict_merge(result[k], v)
        else:
            result[k] = copy.deepcopy(v)
    return result


def lookup_path(container, path, sep='.', createpath=False):
    """
    return (['a','b'],
            [container['a'], container['a']['b']],
            'c')  where path=sep.join(['a','b','c'])

    """
    names = path.split(sep)
    dirnames = names[:-1]
    basename = names[-1]

    node = container
    name_path = []
    node_path = [node]
    for name in dirnames:
        name_path.append(name)
        if name not in node:
            if not createpath:
                m = "'{0}': path not found".format(sep.join(name_path))
                raise KeyError(m)
            node[name] = {}
        try:
            node = node[name]
        except TypeError as e:
            m = "'{0}': cannot traverse path beyond this node: {1}"
            m = m.format(sep.join(name_path), str(e))
            raise ValueError(m)
        node_path.append(node)

    return name_path, node_path, basename


def walk_paths(container):
    for name, node in container.iteritems():
        if not hasattr(node, 'items'):
            yield [name], [node]
        else:
            for names, nodes in walk_paths(node):
                yield [name] + names, [node] + nodes


def list_paths(container, sep='.'):
    """
    >>> sorted(list_paths({'a': {'b': {'c': 'd'}}}))
    [('a.b.c', 'd')]
    >>> sorted(list_paths({'a': {'b': {'c': 'd'}, 'e': 3}}))
    [('a.b.c', 'd'), ('a.e', 3)]
    >>> sorted(list_paths({'a': {'b': {'c': 'd'}, 'e': {'f': 3}}}))
    [('a.b.c', 'd'), ('a.e.f', 3)]
    >>> list_paths({})
    []

    """
    return [(sep.join(name_path), node_path[-1])
            for name_path, node_path in walk_paths(container)]


def del_path(container, path, sep='.', collect=True):
    """
    del container['a']['b']['c'] where path=sep.join(['a','b','c'])

    >>> d = {'a': {'b': {'c': 'd'}}}; del_path(d, 'a.b.c'); d
    {}
    >>> d = {'a': {'b': {'c': 'd'}}}; del_path(d, 'a.b.c', collect=False); d
    {'a': {'b': {}}}
    >>> d = {'a': {'b': {'c': 'd'}}}; del_path(d, 'a.b.c.d')
    Traceback (most recent call last):
    ValueError: 'a.b.c': cannot traverse path beyond this node:\
 'str' object does not support item deletion
    """

    name_path, node_path, basename = \
            lookup_path(container, path, sep=sep, createpath=False)

    lastnode = node_path.pop()
    lastname = basename
    try:
        if basename in lastnode:
            del lastnode[basename]
    except (TypeError, KeyError) as e:
        m = "'{0}': cannot traverse path beyond this node: {1}"
        m = m.format(sep.join(name_path), str(e))
        raise ValueError(m)

    if collect:
        while node_path and not lastnode:
            basename = name_path.pop()
            lastnode = node_path.pop()
            del lastnode[basename]


def get_path(container, path, sep='.'):
    """
    return container['a']['b']['c'] where path=sep.join(['a','b','c'])

    >>> get_path({'a': {'b': {'c': 'd'}}}, 'a.b.c.d')
    Traceback (most recent call last):
    ValueError: 'a.b.c.d': cannot traverse path beyond this node:\
 string indices must be integers, not str
    >>> get_path({'a': {'b': {'c': 1}}}, 'a.b.c.d')
    Traceback (most recent call last):
    ValueError: 'a.b.c.d': cannot traverse path beyond this node:\
 'int' object is unsubscriptable
    >>> get_path({'a': {'b': {'c': 1}}}, 'a.b.c')
    1
    >>> get_path({'a': {'b': {'c': 1}}}, 'a.b')
    {'c': 1}

    """
    name_path, node_path, basename = \
            lookup_path(container, path, sep=sep, createpath=False)
    name_path.append(basename)
    node = node_path[-1]

    try:
        return node[basename]
    except TypeError as e:
        m = "'{0}': cannot traverse path beyond this node: {1}"
        m = m.format(sep.join(name_path), str(e))
        raise ValueError(m)
    except KeyError as e:
        m = "'{0}': path not found: {1}"
        m = m.format(sep.join(name_path), str(e))
        raise KeyError(m)


def set_path(container, path, value, sep='.',
             createpath=False, overwrite=True):
    """
    container['a']['b']['c'] = value where path=sep.join(['a','b','c'])

    >>> set_path({'a': {'b': {'c': 'd'}}}, 'a.b.c.d', 1)
    Traceback (most recent call last):
    ValueError: 'a.b.c.d': cannot traverse path beyond this node:\
 'str' object does not support item assignment
    >>> set_path({'a': {'b': {'c': 'd'}}}, 'a.b.x.d', 1)
    Traceback (most recent call last):
    KeyError: "'a.b.x': path not found"
    >>> set_path({'a': {'b': {'c': 'd'}}}, 'a.b.x.d', 1, createpath=True)
    
    >>> set_path({'a': {'b': {'c': 'd'}}}, 'a.b.c', 1)
     
    >>> set_path({'a': {'b': {'c': 'd'}}}, 'a.b.c', 1, overwrite=False)
    Traceback (most recent call last):
    ValueError: will not overwrite path 'a.b.c'

    """
    name_path, node_path, basename = \
            lookup_path(container, path, sep=sep, createpath=createpath)
    name_path.append(basename)
    node = node_path[-1]

    if basename in node and not overwrite:
        m = "will not overwrite path '{0}'".format(path)
        raise ValueError(m)

    try:
        node[basename] = value
    except TypeError as e:
        m = "'{0}': cannot traverse path beyond this node: {1}"
        m = m.format(sep.join(name_path), str(e))
        raise ValueError(m)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
