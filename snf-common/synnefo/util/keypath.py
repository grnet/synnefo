# Copyright 2013 GRNET S.A. All rights reserved.
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
integer_re = re.compile('-?[0-9]+')


def unpack(pathstr, sep='.'):
    """
    >>> unpack('a.-2.x')
    ['a', -2, 'x']
    """
    names = pathstr.split(sep)
    parse = lambda x: int(x) if integer_re.match(x) else x
    return [parse(x) for x in names]


def lookup_path(container, path, createpath=False):
    """
    return (['a','b'],
            [container['a'], container['a']['b']],
            'c')  where path=['a','b','c']

    """
    dirnames = path[:-1]
    basename = path[-1]

    node = container
    name_path = []
    node_path = [node]
    for name in dirnames:
        name_path.append(name)
        try:
            node = node[name]
        except KeyError as e:
            if not createpath:
                m = "{0}: path not found".format(name_path)
                raise KeyError(m)
            node[name] = {}
            node = node[name]
        except IndexError as e:
            if not createpath:
                m = "{0}: path not found: {1}".format(name_path, e)
                raise KeyError(m)
            size = name if name > 0 else -name
            node += (dict() for _ in xrange(len(node), size))
            node = node[name]
        except TypeError as e:
            m = "{0}: cannot traverse path beyond this node: {1}"
            m = m.format(name_path, str(e))
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


def list_paths(container):
    """
    >>> sorted(list_paths({'a': {'b': {'c': 'd'}}}))
    [(['a', 'b', 'c'], 'd')]
    >>> sorted(list_paths({'a': {'b': {'c': 'd'}, 'e': 3}}))
    [(['a', 'b', 'c'], 'd'), (['a', 'e'], 3)]
    >>> sorted(list_paths({'a': {'b': {'c': 'd'}, 'e': {'f': 3}}}))
    [(['a', 'b', 'c'], 'd'), (['a', 'e', 'f'], 3)]
    >>> sorted(list_paths({'a': [{'b': 3}, 2]}))
    [(['a'], [{'b': 3}, 2])]
    >>> list_paths({})
    []

    """
    return [(name_path, node_path[-1])
            for name_path, node_path in walk_paths(container)]


def del_path(container, path, collect=True):
    """
    del container['a']['b']['c'] where path=['a','b','c']

    >>> d = {'a': {'b': {'c': 'd'}}}; del_path(d, ['a', 'b', 'c']); d
    {}
    >>> d = {'a': {'b': {'c': 'd'}}}; del_path(d, ['a', 'b', 'c'],\
 collect=False); d
    {'a': {'b': {}}}
    >>> d = {'a': {'b': {'c': 'd'}}}; del_path(d, ['a', 'b', 'c', 'd'])
    Traceback (most recent call last):
    ValueError: ['a', 'b', 'c']: cannot traverse path beyond this node:\
 'str' object does not support item deletion
    """

    name_path, node_path, basename = \
        lookup_path(container, path, createpath=False)

    lastnode = node_path.pop()
    try:
        if basename in lastnode:
            del lastnode[basename]
    except (TypeError, KeyError) as e:
        m = "{0}: cannot traverse path beyond this node: {1}"
        m = m.format(name_path, str(e))
        raise ValueError(m)

    if collect:
        while node_path and not lastnode:
            basename = name_path.pop()
            lastnode = node_path.pop()
            del lastnode[basename]


def get_path(container, path):
    """
    return container['a']['b']['c'] where path=['a','b','c']

    >>> get_path({'a': {'b': {'c': 'd'}}}, ['a', 'b', 'c', 'd'])
    Traceback (most recent call last):
    ValueError: ['a', 'b', 'c', 'd']: cannot traverse path beyond this node:\
 string indices must be integers, not str
    >>> get_path({'a': {'b': {'c': 1}}}, ['a', 'b', 'c', 'd'])
    Traceback (most recent call last):
    ValueError: ['a', 'b', 'c', 'd']: cannot traverse path beyond this node:\
 'int' object has no attribute '__getitem__'
    >>> get_path({'a': {'b': {'c': 1}}}, ['a', 'b', 'c'])
    1
    >>> get_path({'a': {'b': {'c': 1}}}, ['a', 'b'])
    {'c': 1}
    >>> get_path({'a': [{'z': 1}]}, ['a', 'b'])
    Traceback (most recent call last):
    ValueError: ['a', 'b']: cannot traverse path beyond this node:\
 list indices must be integers, not str
    >>> get_path({'a': [{'z': 1}]}, ['a', 0])
    {'z': 1}
    >>> get_path({'a': [{'z': 1}]}, ['a', 1])
    Traceback (most recent call last):
    KeyError: "['a', 1]: path not found: list index out of range"
    >>> get_path({'a': [{'z': 1}]}, ['a', 0, 'z'])
    1
    >>> get_path({'a': [{'z': 1}]}, ['a', -1, 'z'])
    1

    """
    name_path, node_path, basename = \
        lookup_path(container, path, createpath=False)
    name_path.append(basename)
    node = node_path[-1]

    try:
        return node[basename]
    except TypeError as e:
        m = "{0}: cannot traverse path beyond this node: {1}"
        m = m.format(name_path, str(e))
        raise ValueError(m)
    except KeyError as e:
        m = "{0}: path not found: {1}"
        m = m.format(name_path, str(e))
        raise KeyError(m)
    except IndexError as e:
        m = "{0}: path not found: {1}"
        m = m.format(name_path, str(e))
        raise KeyError(m)


def set_path(container, path, value, createpath=False, overwrite=True):
    """
    container['a']['b']['c'] = value where path=['a','b','c']

    >>> set_path({'a': {'b': {'c': 'd'}}}, ['a', 'b', 'c', 'd'], 1)
    Traceback (most recent call last):
    ValueError: ['a', 'b', 'c', 'd']: cannot index, node is neither dict nor\
 list
    >>> set_path({'a': {'b': {'c': 'd'}}}, ['a', 'b', 'x', 'd'], 1)
    Traceback (most recent call last):
    KeyError: "['a', 'b', 'x']: path not found"
    >>> set_path({'a': {'b': {'c': 'd'}}}, ['a', 'b', 'x', 'd'], 1,\
 createpath=True)

    >>> set_path({'a': {'b': {'c': 'd'}}}, ['a', 'b', 'c'], 1)

    >>> set_path({'a': {'b': {'c': 'd'}}}, ['a', 'b', 'c'], 1, overwrite=False)
    Traceback (most recent call last):
    ValueError: will not overwrite path ['a', 'b', 'c']
    >>> d = {'a': [{'z': 1}]}; set_path(d, ['a', -2, 1], 2, createpath=False)
    Traceback (most recent call last):
    KeyError: "['a', -2]: path not found: list index out of range"
    >>> d = {'a': [{'z': 1}]}; set_path(d, ['a', -2, 1], 2, createpath=True); \
 d['a'][-2][1]
    2

    """
    name_path, node_path, basename = \
        lookup_path(container, path, createpath=createpath)
    name_path.append(basename)
    node = node_path[-1]

    if basename in node and not overwrite:
        m = "will not overwrite path {0}".format(path)
        raise ValueError(m)

    is_object_node = hasattr(node, 'keys')
    is_list_node = isinstance(node, list)
    if not is_object_node and not is_list_node:
        m = "{0}: cannot index, node is neither dict nor list"
        m = m.format(name_path)
        raise ValueError(m)

    is_integer = isinstance(basename, (int, long))
    if is_list_node and not is_integer:
        m = "{0}: cannot index list node without an integer"
        m = m.format(name_path)
        raise ValueError(m)
    try:
        node[basename] = value
    except TypeError as e:
        m = "{0}: cannot traverse path beyond this node: {1}"
        m = m.format(name_path, str(e))
        raise ValueError(m)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
