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

from httplib import HTTPConnection, HTTP
from sys import stdin

import json
import types
import socket
import pithos.api.faults

ERROR_CODES = {304:'Not Modified',
               400:'Bad Request',
               401:'Unauthorized',
               404:'Not Found',
               409:'Conflict',
               411:'Length Required',
               412:'Precondition Failed',
               416:'Range Not Satisfiable',
               422:'Unprocessable Entity',
               503:'Service Unavailable'}

class Fault(Exception):
    def __init__(self, data='', status=None):
        if data == '' and status in ERROR_CODES.keys():
            data = ERROR_CODES[status]
        Exception.__init__(self, data)
        self.data = data
        self.status = status

class Client(object):
    def __init__(self, host, account, api='v1', verbose=False, debug=False):
        """`host` can also include a port, e.g '127.0.0.1:8000'."""
        
        self.host = host
        self.account = account
        self.api = api
        self.verbose = verbose or debug
        self.debug = debug
    
    def _chunked_transfer(self, path, method='PUT', f=stdin, headers=None,
                          blocksize=1024):
        http = HTTPConnection(self.host)
        
        # write header
        path = '/%s/%s%s' % (self.api, self.account, path)
        http.putrequest(method, path)
        http.putheader('Content-Type', 'application/octet-stream')
        http.putheader('Transfer-Encoding', 'chunked')
        if headers:
            for header,value in headers.items():
                http.putheader(header, value)
        http.endheaders()
        
        # write body
        data = ''
        while True:
            if f.closed:
                break
            block = f.read(blocksize)
            if block == '':
                break
            data = '%s\r\n%s\r\n' % (hex(len(block)), block)
            try:
                http.send(data)
            except:
                #retry
                http.send(data)
        data = '0x0\r\n'
        try:
            http.send(data)
        except:
            #retry
            http.send(data)
        
        # get response
        resp = http.getresponse()
        
        headers = dict(resp.getheaders())
        
        if self.verbose:
            print '%d %s' % (resp.status, resp.reason)
            for key, val in headers.items():
                print '%s: %s' % (key.capitalize(), val)
            print
        
        length = resp.getheader('Content-length', None)
        data = resp.read(length)
        if self.debug:
            print data
            print
        
        if int(resp.status) in ERROR_CODES.keys():
            raise Fault(data, int(resp.status))
        
        #print '*',  resp.status, headers, data
        return resp.status, headers, data
    
    def req(self, method, path, body=None, headers=None, format='text',
            params=None):
        full_path = '/%s/%s%s?format=%s' % (self.api, self.account, path,
                                            format)
        if params:
            for k,v in params.items():
                if v:
                    full_path = '%s&%s=%s' %(full_path, k, v)
        conn = HTTPConnection(self.host)
        
        #encode whitespace
        full_path = full_path.replace(' ', '%20')
        
        kwargs = {}
        kwargs['headers'] = headers or {}
        if not headers or \
        'Transfer-Encoding' not in headers \
        or headers['Transfer-Encoding'] != 'chunked':
            kwargs['headers']['Content-Length'] = len(body) if body else 0
        if body:
            kwargs['body'] = body
            kwargs['headers']['Content-Type'] = 'application/octet-stream'
        #print '****', method, full_path, kwargs
        try:
            conn.request(method, full_path, **kwargs)
        except socket.error, e:
            raise Fault(status=503)
            
        resp = conn.getresponse()
        headers = dict(resp.getheaders())
        
        if self.verbose:
            print '%d %s' % (resp.status, resp.reason)
            for key, val in headers.items():
                print '%s: %s' % (key.capitalize(), val)
            print
        
        length = resp.getheader('Content-length', None)
        data = resp.read(length)
        if self.debug:
            print data
            print
        
        if int(resp.status) in ERROR_CODES.keys():
            raise Fault(data, int(resp.status))
        
        #print '*',  resp.status, headers, data
        return resp.status, headers, data
    
    def delete(self, path, format='text'):
        return self.req('DELETE', path, format=format)
    
    def get(self, path, format='text', headers=None, params=None):
        return self.req('GET', path, headers=headers, format=format,
                        params=params)
    
    def head(self, path, format='text', params=None):
        return self.req('HEAD', path, format=format, params=params)
    
    def post(self, path, body=None, format='text', headers=None):
        return self.req('POST', path, body, headers=headers, format=format)
    
    def put(self, path, body=None, format='text', headers=None):
        return self.req('PUT', path, body, headers=headers, format=format)
    
    def _list(self, path, detail=False, params=None, headers=None):
        format = 'json' if detail else 'text'
        status, headers, data = self.get(path, format=format, headers=headers,
                                         params=params)
        if detail:
            data = json.loads(data)
        else:
            data = data.strip().split('\n')
        return data
    
    def _get_metadata(self, path, prefix=None, params=None):
        status, headers, data = self.head(path, params=params)
        prefixlen = len(prefix) if prefix else 0
        meta = {}
        for key, val in headers.items():
            if prefix and not key.startswith(prefix):
                continue
            elif prefix and key.startswith(prefix):
                key = key[prefixlen:]
            meta[key] = val
        return meta
    
    def _update_metadata(self, path, entity, **meta):
        """
         adds new and updates the values of previously set metadata
        """
        prefix = 'x-%s-meta-' % entity
        prev_meta = self._get_metadata(path, prefix)
        prev_meta.update(meta)
        headers = {}
        for key, val in prev_meta.items():
            key = '%s%s' % (prefix, key)
            key = '-'.join(elem.capitalize() for elem in key.split('-'))
            headers[key] = val
        self.post(path, headers=headers)
    
    def _delete_metadata(self, path, entity, meta=[]):
        """
        delete previously set metadata
        """
        prefix = 'x-%s-meta-' % entity
        prev_meta = self._get_metadata(path, prefix)
        headers = {}
        for key, val in prev_meta.items():
            if key in meta:
                continue
            key = '%s%s' % (prefix, key)
            key = '-'.join(elem.capitalize() for elem in key.split('-'))
            headers[key] = val
        self.post(path, headers=headers)
    
    # Storage Account Services
    
    def list_containers(self, detail=False, params=None, headers=None):
        return self._list('', detail, params, headers)
    
    def account_metadata(self, restricted=False, until=None):
        prefix = 'x-account-meta-' if restricted else None
        params = {'until':until} if until else None
        return self._get_metadata('', prefix, params=params)
    
    def update_account_metadata(self, **meta):
        self._update_metadata('', 'account', **meta)
        
    def delete_account_metadata(self, meta=[]):
        self._delete_metadata('', 'account', meta)
    
    def set_account_groups(self, groups):
        headers = {}
        for key, val in groups.items():
            headers['X-Account-Group-%s' % key.capitalize()] = val
        self.post('', headers=headers)
    
    # Storage Container Services
    
    def _filter(self, l, d):
        """
        filter out from l elements having the metadata values provided
        """
        ll = l
        for elem in l:
            if type(elem) == types.DictionaryType:
                for key in d.keys():
                    k = 'x_object_meta_%s' % key
                    if k in elem.keys() and elem[k] == d[key]:
                        ll.remove(elem)
                        break
        return ll
    
    def _filter_trashed(self, l):
        return self._filter(l, {'trash':'true'})
    
    def list_objects(self, container, detail=False, params=None, headers=None,
                     include_trashed=False):
        l = self._list('/' + container, detail, params, headers)
        if not include_trashed:
            l = self._filter_trashed(l)
        return l
    
    def create_container(self, container, headers=None):
        status, header, data = self.put('/' + container, headers=headers)
        if status == 202:
            return False
        elif status != 201:
            raise Fault(data, int(status))
        return True
    
    def delete_container(self, container):
        self.delete('/' + container)
    
    def retrieve_container_metadata(self, container, restricted=False,
                                    until=None):
        prefix = 'x-container-meta-' if restricted else None
        params = {'until':until} if until else None
        return self._get_metadata('/%s' % container, prefix, params=params)
    
    def update_container_metadata(self, container, **meta):
        self._update_metadata('/' + container, 'container', **meta)
        
    def delete_container_metadata(self, container, meta=[]):
        path = '/%s' % (container)
        self._delete_metadata(path, 'container', meta)
    
    # Storage Object Services
    
    def retrieve_object(self, container, object, detail=False, headers=None,
                        version=None):
        path = '/%s/%s' % (container, object)
        format = 'json' if detail else 'text'
        params = {'version':version} if version else None 
        status, headers, data = self.get(path, format, headers, params)
        return data
    
    def create_directory_marker(self, container, object):
        if not object:
            raise Fault('Directory markers have to be nested in a container')
        h = {'Content-Type':'application/directory'}
        self.create_object(container, object, f=None, headers=h)
    
    def create_object(self, container, object, f=stdin, chunked=False,
                      blocksize=1024, headers=None):
        """
        creates an object
        if f is None then creates a zero length object
        if f is stdin or chunked is set then performs chunked transfer 
        """
        path = '/%s/%s' % (container, object)
        if not chunked and f != stdin:
            data = f.read() if f else None
            return self.put(path, data, headers=headers)
        else:
            return self._chunked_transfer(path, 'PUT', f, headers=headers,
                                   blocksize=1024)
    
    def update_object(self, container, object, f=stdin, chunked=False,
                      blocksize=1024, headers=None):
        if not f:
            return
        path = '/%s/%s' % (container, object)
        if not chunked and f != stdin:
            data = f.read()
            self.post(path, data, headers=headers)
        else:
            self._chunked_transfer(path, 'POST', f, headers=headers,
                                   blocksize=1024)
    
    def _change_obj_location(self, src_container, src_object, dst_container,
                             dst_object, remove=False, headers=None):
        path = '/%s/%s' % (dst_container, dst_object)
        if not headers:
            headers = {}
        if remove:
            headers['X-Move-From'] = '/%s/%s' % (src_container, src_object)
        else:
            headers['X-Copy-From'] = '/%s/%s' % (src_container, src_object)
        headers['Content-Length'] = 0
        self.put(path, headers=headers)
    
    def copy_object(self, src_container, src_object, dst_container,
                             dst_object, headers=None):
        self._change_obj_location(src_container, src_object,
                                   dst_container, dst_object,
                                   headers=headers)
    
    def move_object(self, src_container, src_object, dst_container,
                             dst_object, headers=None):
        self._change_obj_location(src_container, src_object,
                                   dst_container, dst_object, True, headers)
    
    def delete_object(self, container, object):
        self.delete('/%s/%s' % (container, object))
    
    def retrieve_object_metadata(self, container, object, restricted=False,
                                 version=None):
        path = '/%s/%s' % (container, object)
        prefix = 'x-object-meta-' if restricted else None
        params = {'version':version} if version else None
        return self._get_metadata(path, prefix, params=params)
    
    def update_object_metadata(self, container, object, **meta):
        path = '/%s/%s' % (container, object)
        self._update_metadata(path, 'object', **meta)
    
    def delete_object_metadata(self, container, object, meta=[]):
        path = '/%s/%s' % (container, object)
        self._delete_metadata(path, 'object', meta)
    
    def trash_object(self, container, object):
        """
        trashes an object
        actually resets all object metadata with trash = true 
        """
        path = '/%s/%s' % (container, object)
        meta = {'trash':'true'}
        self._update_metadata(path, 'object', **meta)
    
    def restore_object(self, container, object):
        """
        restores a trashed object
        actualy removes trash object metadata info
        """
        self.delete_object_metadata(container, object, ['trash'])

