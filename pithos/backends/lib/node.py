# Copyright 2011 GRNET S.A. All rights reserved.
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

from time import time

from dbworker import DBWorker


ROOTNODE  = 0

( SERIAL, NODE, SIZE, SOURCE, MTIME, CLUSTER ) = range(6)

inf = float('inf')


def strnextling(prefix):
    """return the first unicode string
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
    s += unichr(c+1)
    return s

def strprevling(prefix):
    """return an approximation of the last unicode string
       less than but not starting with given prefix.
       strprevling(u'hello') -> u'helln\\xffff'
    """
    if not prefix:
        ## There is no prevling for the null string
        return prefix
    s = prefix[:-1]
    c = ord(prefix[-1])
    if c > 0:
        s += unichr(c-1) + unichr(0xffff)
    return s


import re
_regexfilter = re.compile('(!?)\s*([\w-]+)\s*(=|!=|<=|>=|<|>)?\s*(.*)$', re.UNICODE)

_propnames = {
    'serial'    : 0,
    'node'      : 1,
    'size'      : 2,
    'source'    : 3,
    'mtime'     : 4,
    'cluster'   : 5,
}


class Node(DBWorker):
    """Nodes store path organization.
       Versions store obejct history.
       Attributes store metadata.
    """
    
    def __init__(self, **params):
        execute = self.execute
        
        execute(""" pragma foreign_keys = on """)
        
        execute(""" create table if not exists nodes
                          ( node       integer primary key,
                            parent     integer not null default 0,
                            path       text    not null default ''
                            foreign key (parent)
                            references nodes(node)
                            on update cascade
                            on delete cascade )""")
        execute(""" create unique index if not exists idx_nodes_path
                    on nodes(path) """)
        
        execute(""" create table if not exists statistics
                          ( node       integer not null,
                            population integer not null default 0,
                            size       integer not null default 0,
                            mtime      integer,
                            cluster    integer not null default 0,
                            primary key (node, cluster)
                            foreign key (node)
                            references nodes(node)
                            on update cascade
                            on delete cascade )""")
        
        execute(""" create table if not exists versions
                          ( serial     integer primary key,
                            node       integer not null,
                            size       integer not null default 0,
                            source     integer,
                            mtime      integer,
                            cluster    integer not null default 0,
                            foreign key (node)
                            references nodes(node)
                            on update cascade
                            on delete cascade ) """)
        # execute(""" create index if not exists idx_versions_path
        #             on nodes(cluster, node, path) """)
        # execute(""" create index if not exists idx_versions_mtime
        #             on nodes(mtime) """)
        
        execute(""" create table if not exists attributes
                          ( serial integer,
                            key    text,
                            value  text,
                            primary key (serial, key)
                            foreign key (serial)
                            references versions(serial)
                            on update cascade
                            on delete cascade ) """)
        
        q = "insert or ignore into nodes(node, parent) values (?, ?)"
        execute(q, (ROOTNODE, ROOTNODE))
    
    def node_update_ancestors(self, node, population, size, mtime, cluster=0):
        """Update the population properties of the given node.
           Population properties keep track the population and total
           size of objects in the node's namespace.
           May be zero or positive or negative numbers.
        """
        
        qs = ("select population, size from statistics"
              "where node = ? and cluster = ?")
        qu = ("insert or replace into statistics (node, population, size, mtime, cluster) "
              "values (?, ?, ?, ?, ?)")
        qp = "select parent from nodes where serial = ?"
        execute = self.execute
        fetchone = self.fetchone
        while 1:
            execute(qs, (node, cluster))
            r = fetchone()
            if r is None:
                prepopulation, presize = (0, 0)
            else:
                prepopulation, presize = r
            population += prepopulation
            size += presize
            
            execute(qu, (node, population, size, mtime, cluster))
            if node == 0:
                break
            
            population = 0 # Population isn't recursive
            execute(qp, (node,))
            r = fetchone()
            if r is None:
                break
            node = r[0]
    
    def node_statistics(self, node, cluster=0):
        """Return population, total size and last mtime
           for all versions under node that belong to the cluster.
        """
        
        q = ("select population, size, mtime from statistics"
             "where node = ? and cluster = ?")
        self.execute(q, (node, cluster))
        r = fetchone()
        if r is None:
            return (0, 0, 0)
        return r
    
    def version_create(self, node, size, source, cluster=0):
        """Create a new version from the given properties.
           Return the (serial, mtime) of the new version.
        """
        
        q = ("insert into nodes (node, size, source, mtime, cluster) "
             "values (?, ?, ?, ?, ?)")
        mtime = time()
        props = (node, path, size, source, mtime, cluster)
        serial = self.execute(q, props).lastrowid
        self.node_update_ancestors(node, 1, size, mtime, cluster)
        return serial, mtime
    
#     def node_remove(self, serial, recursive=0):
#         """Remove the node specified by serial.
#            Return false if the node is not found,
#            or has ancestors and recursive is not set.
#         """
#         
#         props = self.node_get_properties(serial)
#         if props is None:
#             return False
#         size = props[SIZE]
#         parent = props[PARENT]
#         pop = props[POPULATION]
#         popsize = props[POPSIZE]
#         if pop and not recursive:
#             return False
#         
#         q = ("delete from nodes where serial = ?")
#         self.execute(q, (serial,))
#         self.node_update_ancestors(parent, -pop-1, -size-popsize)
#         return True
    
    def version_get_properties(self, serial, keys=(), propnames=_propnames):
        """Return a sequence of values for the properties of
           the version specified by serial and the keys, in the order given.
           If keys is empty, return all properties in the order
           (serial, node, size, source, mtime, cluster).
        """
        
        q = ("select serial, node, path, size, source, mtime, cluster "
             "from nodes "
             "where serial = ?")
        self.execute(q, (serial,))
        r = self.fetchone()
        if r is None:
            return r
        
        if not keys:
            return r
        return [r[propnames[k]] for k in keys if k in propnames]
    
#     def node_set_properties(self, serial, items, propnames=_mutablepropnames):
#         """Set the properties of a node specified by the node serial and
#            the items iterable of (name, value) pairs.
#            Mutable properties are %s.
#            Invalid property names and 'serial' are not set.
#         """ % (_mutables,)
#         
#         if not items:
#             return
#         
#         keys, vals = zip(*items)
#         keystr = ','.join(("%s = ?" % k) for k in keys if k in propnames)
#         if not keystr:
#             return
#         q = "update nodes set %s where serial = ?" % keystr
#         vals += (serial,)
#         self.execute(q, vals)
    
    def version_lookup(self, node, before=inf, cluster=0):
        """Lookup the current version of the given node.
           Return a list with its properties:
           (serial, node, size, source, mtime, cluster)
           or None if the version is not found.
        """
        
        q = ("select serial, node, size, source, mtime, cluster "
             "from nodes "
             "where serial = (select max(serial) "
                             "from nodes "
                             "where node = ? and cluster = ? and mtime < ?)")
        self.execute(q, (node, cluster, before))
        props = self.fetchone()
        if props is not None:
            return props
        return None
    
    def node_lookup(self, path):
        """Lookup the current node of the given path.
           Return None if the path is not found.
        """
        
        q = ("select node from nodes where path = ?")
        self.execute(q, (path,))
        r = self.fetchone()
        if r is not None:
            return r[0]
        return None
    
    def node_create(self, parent, path):
        """Create a new node from the given properties.
           Return the node identifier of the new node.
        """
        
        q = ("insert into nodes (parent, path) "
             "values (?, ?)")
        props = (parent, path)
        return self.execute(q, props).lastrowid
    
    def parse_filters(self, filterq):
        preterms = filterq.split(',')
        included = []
        excluded = []
        opers = []
        match = _regexfilter.match
        for term in preterms:
            m = match(term)
            if m is None:
                continue
            neg, key, op, value = m.groups()
            if neg:
                excluded.append(key)
            elif not value:
                included.append(key)
            elif op:
                opers.append((key, op, value))
        
        return included, excluded, opers
    
    def construct_filters(self, filterq):
        subqlist = []
        append = subqlist.append
        included, excluded, opers = self.parse_filters(filterq)
        args = []
        
        if included:
            subq = "key in ("
            subq += ','.join(('?' for x in included)) + ")"
            args += included
            append(subq)
        
        if excluded:
            subq = "key not in ("
            subq += ','.join(('?' for x in exluded)) + ")"
            args += excluded
            append(subq)
        
        if opers:
            t = (("(key = %s and value %s %s)" % (k, o, v)) for k, o, v in opers)
            subq = "(" + ' or '.join(t) + ")"
            args += opers
        
        if not subqlist:
            return None, None
        
        subq = " and serial in (select serial from attributes where "
        subq += ' and '.join(subqlist)
        subq += ")"
        
        return subq, args
    
#     def node_list(self, parent, prefix='',
#                    start='', delimiter=None,
#                    after=0.0, before=inf,
#                    filterq=None, versions=0,
#                    cluster=0, limit=10000):
#         """Return (a list of property tuples, a list of common prefixes)
#            for the current versions of the paths with the given parent,
#            matching the following criteria.
#            
#            The property tuple for a version is returned if all
#            of these conditions are true:
#            
#                 a. parent (and cluster) matches
#                 
#                 b. path > start
#                 
#                 c. path starts with prefix
#                 
#                 d. i  [versions=true]  version is in (after, before)
#                    ii [versions=false] version is the max in (after, before)
#                 
#                 e. the path does not have the delimiter occuring
#                    after the prefix.
#                 
#                 f. serial matches the attribute filter query.
#                    
#                    A filter query is a comma-separated list of
#                    terms in one of these three forms:
#                    
#                    key
#                        an attribute with this key must exist
#                    
#                    !key
#                        an attribute with this key must not exist
#                    
#                    key ?op value
#                        the attribute with this key satisfies the value
#                        where ?op is one of ==, != <=, >=, <, >.
#            
#            matching up to the first delimiter after prefix,
#            and are reported only once, as "virtual directories".
#            The delimiter is included in the prefixes.
#            Prefixes do appear from (e) even if no paths would match in (f).
#            
#            If arguments are None, then the corresponding matching rule
#            will always match.
#         """
#         
#         execute = self.execute
# 
#         if start < prefix:
#             start = strprevling(prefix)
# 
#         nextling = strnextling(prefix)
# 
#         q = ("select serial, parent, path, size, "
#                     "population, popsize, source, mtime, cluster "
#              "from nodes "
#              "where parent = ? and path > ? and path < ? "
#              "and mtime > ? and mtime < ? and cluster = ?")
#         args = [parent, start, nextling, after, before, cluster]
# 
#         if filterq:
#             subq, subargs = self.construct_filters(filterq)
#             if subq is not None:
#                 q += subq
#                 args += subargs
#         q += " order by path"
# 
#         if delimiter is None:
#             q += " limit ?"
#             args.append(limit)
#             execute(q, args)
#             return self.fetchall(), ()
# 
#         pfz = len(prefix)
#         dz = len(delimiter)
#         count = 0
#         fetchone = self.fetchone
#         prefixes = []
#         pappend = prefixes.append
#         matches = []
#         mappend = matches.append
#         
#         execute(q, args)
#         while 1:
#             props = fetchone()
#             if props is None:
#                 break
#             path = props[PATH]
#             idx = path.find(delimiter, pfz)
#             if idx < 0:
#                 mappend(props)
#                 count += 1
#                 if count >= limit:
#                     break
#                 continue
# 
#             pf = path[:idx + dz]
#             pappend(pf)
#             count += 1
#             ## XXX: if we break here due to limit,
#             ##      but a path would also be matched below,
#             ##      the path match would be lost since the
#             ##      next call with start=path would skip both of them.
#             ##      In this case, it is impossible to obey the limit,
#             ##      therefore we will break later, at limit + 1.
#             if idx + dz == len(path):
#                 mappend(props)
#                 count += 1
# 
#             if count >= limit: 
#                 break
# 
#             args[1] = strnextling(pf) # new start
#             execute(q, args)
# 
#         return matches, prefixes

#     def node_delete(self, parent, prefix,
#                     start='', delimiter=None,
#                     after=0.0, before=inf,
#                     filterq=None, versions=0,
#                     cluster=0, limit=10000):
#         """Delete the matching version for each
#            of the matching paths in the parent's namespace.
#            Return empty if nothing is deleted, else return matches.
#            The paths matching are those that would
#            be returned by .node_list() with the same arguments.
#            Note that only paths are deleted, not prefixes.
# 
#         """
#         r = self.node_list(parent, prefix,
#                            start=start, delimiter=delimiter,
#                            after=after, before=before,
#                            filterq=filterq, versions=versions,
#                            cluster=cluster, limit=limit)
#         matches, prefixes = r
#         if not matches:
#             return ()
# 
#         q = "delete from nodes where serial = ?"
#         self.executemany(q, ((props[SERIAL],) for props in matches))
#         # TODO: Update sizes.
#         return matches

#     def node_purge(self, parent, path, after=0, before=inf, cluster=0):
#         """Delete all nodes with the specified
#            parent, cluster and path, and return
#            the serials of nodes deleted.
#         """
#         execute = self.execute
#         q = ("select count(serial), total(size), "
#                     "total(population), total(popsize) "
#              "from nodes "
#              "where parent = ? and cluster = ? "
#              "and path = ? and mtime between ? and ?")
#         args = (parent, cluster, path, after, before)
#         execute(q, args)
#         nr, size, pop, popsize = self.fetchone()
#         if not nr:
#             return ()
#         self.node_update_ancestors(parent, -pop-nr, -size-popsize)
#         q = ("select serial from nodes "
#              "where parent = ? and cluster = ? "
#              "and path = ? and mtime between ? and ?")
#         execute(q, args)
#         serials = [r[SERIAL] for r in self.fetchall()]
#         q = ("delete from nodes where "
#              "parent = ? and cluster = ? "
#              "and path = ? and mtime between ? and ?")
#         execute(q, args)
#         return serials

#     def node_move(self, source, parent, path):
#         """Move the source node into another path,
#            possibly, in another parent's namespace.
#            The node is moved with its namespace.
#         """
#         props = self.node_get_properties(source)
# 
#         oldparent = props[PARENT]
#         size = props[SIZE]
#         population = props[POPULATION]
#         popsize = props[POPSIZE]
# 
#         sizedelta = size + popsize
#         popdelta = population + 1
#         node_update_ancestors = self.node_update_ancestors
#         node_update_ancestors(oldparent, -popdelta, -sizedelta)
#         node_update_ancestors(parent, popdelta, sizedelta)
# 
#         q = "update nodes set parent = ?, path = ? where serial = ?"
#         self.execute(q, (parent, path, source))

    def version_copy(self, serial, node=None, copy_attr=True):
        """Copy the version specified by serial into
           a new version of node. Optionally copy attributes.
           Return the (serial, mtime) of the new version.
        """
        
        props = self.version_get_properties(serial)
        size = props[SIZE]
        cluster = props[CLUSTER]
        new_serial, mtime = self.version_create(node, path, size, serial, cluster)
        if copy_attr:
            self.attr_copy(serial, new_serial)
        return (new_serial, mtime)
    
    def node_get_attributes(self, serial, keys=()):
        """Return a list of (key, value) pairs of the node specified by serial.
           If keys is empty, return all attributes.
           Othwerise, return only those specified.
        """
        
        execute = self.execute
        if keys:
            marks = ','.join('?' for k in keys)
            q = ("select key, value from attributes "
                 "where key in (%s) and serial = ?" % (marks,))
            execute(q, keys + (serial,))
        else:
            q = "select key, value from attributes where serial = ?"
            execute(q, (serial,))
        return self.fetchall()
    
    def attr_set(self, serial, items):
        """Set the attributes of the node specified by serial.
           Receive attributes as an iterable of (key, value) pairs.
        """
        
        q = ("insert or replace into attributes (serial, key, value) "
             "values (?, ?, ?)")
        self.executemany(q, ((serial, k, v) for k, v in items))
    
    def attr_del(self, serial, keys=()):
        """Delete attributes of the node specified by serial.
           If keys is empty, delete all attributes.
           Otherwise delete those specified.
        """
        
        if keys:
            q = "delete from attributes where serial = ? and key = ?"
            self.executemany(q, ((serial, key) for key in keys))
        else:
            q = "delete from attributes where serial = ?"
            self.execute(q, (serial,))
    
#     def node_get_attribute_keys(self, parent):
#         """Return a list with all keys pairs defined
#            for the namespace of the node specified.
#         """
#         
#         q = ("select distinct key from attributes a, versions v, nodes n "
#              "where a.serial = v.serial and v.node = n.node and n.parent = ?")
#         self.execute(q, (parent,))
#         return [r[0] for r in self.fetchall()]
    
    def attr_copy(self, source, dest):
        q = ("insert or replace into attributes "
             "select ?, key, value from attributes "
             "where serial = ?")
        self.execute(q, (dest, source))
