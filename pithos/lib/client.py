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
from xml.dom import minidom

import json
import types
import socket
import urllib
import datetime

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
    def __init__(self, host, token, account, api='v1', verbose=False, debug=False):
        """`host` can also include a port, e.g '127.0.0.1:8000'."""
        
        self.host = host
        self.account = account
        self.api = api
        self.verbose = verbose or debug
        self.debug = debug
        self.token = token
    
    def _req(self, method, path, body=None, headers={}, format='text',
             params={}, top_level_req=False):
        #path = urllib.quote(path)
        account = '' if top_level_req else self.account
        full_path = '/%s/%s%s?format=%s' % (self.api, account, path, format)
        
        for k,v in params.items():
            if v:
                full_path = '%s&%s=%s' %(full_path, k, v)
            else:
                full_path = '%s&%s' %(full_path, k)
        conn = HTTPConnection(self.host)
        
        #encode whitespace
        full_path = full_path.replace(' ', '%20')
        
        kwargs = {}
        for k,v in headers.items():
            headers.pop(k)
            k = k.replace('_', '-')
            headers[k] = v
        
        kwargs['headers'] = headers
        kwargs['headers']['X-Auth-Token'] = self.token
        if body:
            kwargs['body'] = body
            kwargs['headers'].setdefault('content-type',
                                         'application/octet-stream')
        kwargs['headers'].setdefault('content-length', len(body) if body else 0)
        #kwargs['headers'] = _encode_headers(kwargs['headers'])
        
        #print '#', method, full_path, kwargs
        t1 = datetime.datetime.utcnow()
        conn.request(method, full_path, **kwargs)
        
        resp = conn.getresponse()
        t2 = datetime.datetime.utcnow()
        #print 'response time:', str(t2-t1)
        headers = dict(resp.getheaders())
        
        if self.verbose:
            print '%d %s' % (resp.status, resp.reason)
            for key, val in headers.items():
                print '%s: %s' % (key.capitalize(), val)
            print
        
        length = resp.getheader('content-length', None)
        data = resp.read(length)
        if self.debug:
            print data
            print
        
        if int(resp.status) in ERROR_CODES.keys():
            raise Fault(data, int(resp.status))
        
        #print '**',  resp.status, headers, data
        return resp.status, headers, data
    
    def delete(self, path, format='text', params={}):
        return self._req('DELETE', path, format=format, params=params)
    
    def get(self, path, format='text', headers={}, params={},
            top_level_req=False):
        return self._req('GET', path, headers=headers, format=format,
                        params=params, top_level_req=top_level_req)
    
    def head(self, path, format='text', params={}):
         return self._req('HEAD', path, format=format, params=params)
    
    def post(self, path, body=None, format='text', headers=None, params={}):
        return self._req('POST', path, body, headers=headers, format=format,
                        params=params)
    
    def put(self, path, body=None, format='text', headers=None):
        return self._req('PUT', path, body, headers=headers, format=format)
    
    def _list(self, path, format='text', params={}, top_level_req=False, 
              **headers):
        status, headers, data = self.get(path, format=format, headers=headers,
                                         params=params,
                                         top_level_req=top_level_req)
        if format == 'json':
            data = json.loads(data) if data else ''
        elif format == 'xml':
            data = minidom.parseString(data)
        else:
            data = data.strip().split('\n') if data else ''
        return data
    
    def _get_metadata(self, path, prefix=None, params={}):
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
    
class OOS_Client(Client):
    """Openstack Object Storage Client"""
    
    def _update_metadata(self, path, entity, **meta):
        """adds new and updates the values of previously set metadata"""
        ex_meta = self.retrieve_account_metadata(restricted=True)
        ex_meta.update(meta)
        headers = {}
        prefix = 'x-%s-meta-' % entity
        for k,v in ex_meta.items():
            k = '%s%s' % (prefix, k)
            headers[k] = v
        return self.post(path, headers=headers)
    
    def _reset_metadata(self, path, entity, **meta):
        """
        overwrites all user defined metadata
        """
        headers = {}
        prefix = 'x-%s-meta-' % entity
        for k,v in meta.items():
            k = '%s%s' % (prefix, k)
            headers[k] = v
        return self.post(path, headers=headers)
    
    def _delete_metadata(self, path, entity, meta=[]):
        """delete previously set metadata"""
        ex_meta = self.retrieve_account_metadata(restricted=True)
        headers = {}
        prefix = 'x-%s-meta-' % entity
        for k in ex_meta.keys():
            if k in meta:
                headers['%s%s' % (prefix, k)] = ex_meta[k]
        return self.post(path, headers=headers)
    
    # Storage Account Services
    
    def list_containers(self, format='text', limit=None, marker=None, params={},
                        **headers):
        """lists containers"""
        params.update({'limit':limit, 'marker':marker})
        return self._list('', format, params, **headers)
    
    def retrieve_account_metadata(self, restricted=False, **params):
        """returns the account metadata"""
        prefix = 'x-account-meta-' if restricted else None
        return self._get_metadata('', prefix, params)
    
    def update_account_metadata(self, **meta):
        """updates the account metadata"""
        return self._update_metadata('', 'account', **meta)
        
    def delete_account_metadata(self, meta=[]):
        """deletes the account metadata"""
        return self._delete_metadata('', 'account', meta)
    
    def reset_account_metadata(self, **meta):
        """resets account metadata"""
        return self._reset_metadata('', 'account', **meta)
    
    # Storage Container Services
    
    def _filter_trashed(self, l):
        return self._filter(l, {'trash':'true'})
    
    def list_objects(self, container, format='text', limit=None, marker=None,
                     prefix=None, delimiter=None, path=None,
                     include_trashed=False, params={}, **headers):
        """returns a list with the container objects"""
        params.update({'limit':limit, 'marker':marker, 'prefix':prefix,
                       'delimiter':delimiter, 'path':path})
        l = self._list('/' + container, format, params, **headers)
        #TODO support filter trashed with xml also
        if format != 'xml' and not include_trashed:
            l = self._filter_trashed(l)
        return l
    
    def create_container(self, container, **meta):
        """creates a container"""
        headers = {}
        for k,v in meta.items():
            headers['x-container-meta-%s' %k.strip().upper()] = v.strip()
        status, header, data = self.put('/' + container, headers=headers)
        if status == 202:
            return False
        elif status != 201:
            raise Fault(data, int(status))
        return True
    
    def delete_container(self, container, params={}):
        """deletes a container"""
        return self.delete('/' + container, params=params)
    
    def retrieve_container_metadata(self, container, restricted=False, **params):
        """returns the container metadata"""
        prefix = 'x-container-meta-' if restricted else None
        return self._get_metadata('/%s' % container, prefix, params)
    
    def update_container_metadata(self, container, **meta):
        """unpdates the container metadata"""
        return self._update_metadata('/' + container, 'container', **meta)
        
    def delete_container_metadata(self, container, meta=[]):
        """deletes the container metadata"""
        path = '/%s' % (container)
        return self._delete_metadata(path, 'container', meta)
    
    # Storage Object Services
    
    def request_object(self, container, object, format='text', params={},
                        **headers):
        """returns tuple containing the status, headers and data response for an object request"""
        path = '/%s/%s' % (container, object)
        status, headers, data = self.get(path, format, headers, params)
        return status, headers, data
    
    def retrieve_object(self, container, object, format='text', params={},
                             **headers):
        """returns an object's data"""
        t = self.request_object(container, object, format, params, **headers)
        return t[2]
    
    def create_directory_marker(self, container, object):
        """creates a dierectory marker"""
        if not object:
            raise Fault('Directory markers have to be nested in a container')
        h = {'content_type':'application/directory'}
        return self.create_zero_length_object(container, object, **h)
    
    def create_object(self, container, object, f=stdin, format='text', meta={},
                      etag=None, content_type=None, content_encoding=None,
                      content_disposition=None, **headers):
        """creates a zero-length object"""
        path = '/%s/%s' % (container, object)
        for k, v  in headers.items():
            if not v:
                headers.pop(k)
        
        l = ['etag', 'content_encoding', 'content_disposition', 'content_type']
        l = [elem for elem in l if eval(elem)]
        for elem in l:
            headers.update({elem:eval(elem)})
            
        for k,v in meta.items():
            headers['x-object-meta-%s' %k.strip()] = v.strip()
        data = f.read() if f else None
        return self.put(path, data, format, headers=headers)
    
    def create_zero_length_object(self, container, object, meta={}, etag=None,
                                  content_type=None, content_encoding=None,
                                  content_disposition=None, **headers):
        args = locals()
        for elem in ['self', 'container', 'headers']:
            args.pop(elem)
        args.update(headers)
        return self.create_object(container, f=None, **args)
    
    def update_object(self, container, object, f=stdin, offset=None, meta={},
                      content_length=None, content_type=None,
                      content_encoding=None, content_disposition=None,
                      **headers):
        path = '/%s/%s' % (container, object)
        for k, v  in headers.items():
            if not v:
                headers.pop(k)
        
        l = ['content_encoding', 'content_disposition', 'content_type',
             'content_length']
        l = [elem for elem in l if eval(elem)]
        for elem in l:
            headers.update({elem:eval(elem)})
            
        if 'content_range' not in headers.keys():
            if offset != None:
                headers['content_range'] = 'bytes %s-/*' % offset
            else:
                headers['content_range'] = 'bytes */*'
            
        for k,v in meta.items():
            headers['x-object-meta-%s' %k.strip()] = v.strip()
        data = f.read() if f else None
        return self.post(path, data, headers=headers)
    
    def _change_obj_location(self, src_container, src_object, dst_container,
                             dst_object, remove=False, meta={}, **headers):
        path = '/%s/%s' % (dst_container, dst_object)
        headers = {} if not headers else headers
        for k, v in meta.items():
            headers['x-object-meta-%s' % k] = v
        if remove:
            headers['x-move-from'] = '/%s/%s' % (src_container, src_object)
        else:
            headers['x-copy-from'] = '/%s/%s' % (src_container, src_object)
        headers['content_length'] = 0
        return self.put(path, headers=headers)
    
    def copy_object(self, src_container, src_object, dst_container, dst_object,
                    meta, **headers):
        """copies an object"""
        return self._change_obj_location(src_container, src_object,
                                   dst_container, dst_object, remove=False,
                                   meta=meta, **headers)
    
    def move_object(self, src_container, src_object, dst_container,
                             dst_object, meta={}, **headers):
        """moves an object"""
        return self._change_obj_location(src_container, src_object,
                                         dst_container, dst_object, remove=True,
                                         meta=meta, **headers)
    
    def delete_object(self, container, object, params={}):
        """deletes an object"""
        return self.delete('/%s/%s' % (container, object), params=params)
    
    def retrieve_object_metadata(self, container, object, restricted=False,
                                 version=None):
        """
        set restricted to True to get only user defined metadata
        """
        path = '/%s/%s' % (container, object)
        prefix = 'x-object-meta-' if restricted else None
        params = {'version':version} if version else {}
        return self._get_metadata(path, prefix, params=params)
    
    def update_object_metadata(self, container, object, **meta):
        """
        updates object's metadata
        """
        path = '/%s/%s' % (container, object)
        return self._update_metadata(path, 'object', **meta)
    
    def delete_object_metadata(self, container, object, meta=[]):
        """
        deletes object's metadata
        """
        path = '/%s/%s' % (container, object)
        return self._delete_metadata(path, 'object', meta)
    
class Pithos_Client(OOS_Client):
    """Pithos Storage Client. Extends OOS_Client"""
    
    def _chunked_transfer(self, path, method='PUT', f=stdin, headers=None,
                          blocksize=1024):
        """perfomrs a chunked request"""
        http = HTTPConnection(self.host)
        
        # write header
        path = '/%s/%s%s' % (self.api, self.account, path)
        http.putrequest(method, path)
        http.putheader('x-auth-token', self.token)
        http.putheader('content-type', 'application/octet-stream')
        http.putheader('transfer-encoding', 'chunked')
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
            data = '%x\r\n%s\r\n' % (len(block), block)
            try:
                http.send(data)
            except:
                #retry
                http.send(data)
        data = '0\r\n\r\n'
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
    
    def _update_metadata(self, path, entity, **meta):
        """
        adds new and updates the values of previously set metadata
        """
        params = {'update':None}
        headers = {}
        prefix = 'x-%s-meta-' % entity
        for k,v in meta.items():
            k = '%s%s' % (prefix, k)
            headers[k] = v
        return self.post(path, headers=headers, params=params)
    
    def _delete_metadata(self, path, entity, meta=[]):
        """
        delete previously set metadata
        """
        params = {'update':None}
        headers = {}
        prefix = 'x-%s-meta-' % entity
        for m in meta:
            headers['%s%s' % (prefix, m)] = ''
        return self.post(path, headers=headers, params=params)
    
    # Storage Account Services
    
    def list_containers(self, format='text', if_modified_since=None,
                        if_unmodified_since=None, limit=1000, marker=None,
                        until=None):
        """returns a list with the account containers"""
        params = {'until':until} if until else {}
        headers = {'if-modified-since':if_modified_since,
                   'if-unmodified-since':if_unmodified_since}
        return OOS_Client.list_containers(self, format=format, limit=limit,
                                          marker=marker, params=params,
                                          **headers)
    
    def retrieve_account_metadata(self, restricted=False, until=None):
        """returns the account metadata"""
        params = {'until':until} if until else {}
        return OOS_Client.retrieve_account_metadata(self, restricted=restricted,
                                                   **params)
    
    def set_account_groups(self, **groups):
        """create account groups"""
        headers = {}
        for k, v in groups.items():
            headers['x-account-group-%s' % k] = v
        params = {'update':None}
        return self.post('', headers=headers, params=params)
    
    def retrieve_account_groups(self):
        """returns the account groups"""
        meta = self.retrieve_account_metadata()
        prefix = 'x-account-group-'
        prefixlen = len(prefix)
        groups = {}
        for key, val in meta.items():
            if prefix and not key.startswith(prefix):
                continue
            elif prefix and key.startswith(prefix):
                key = key[prefixlen:]
            groups[key] = val
        return groups
    
    def unset_account_groups(self, groups=[]):
        """delete account groups"""
        headers = {}
        for elem in groups:
            headers['x-account-group-%s' % elem] = ''
        params = {'update':None}
        return self.post('', headers=headers, params=params)
    
    def reset_account_groups(self, **groups):
        """overrides account groups"""
        headers = {}
        for k, v in groups.items():
            v = v.strip()
            headers['x-account-group-%s' % k] = v
        meta = self.retrieve_account_metadata(restricted=True)
        prefix = 'x-account-meta-'
        for k,v in meta.items():
            k = '%s%s' % (prefix, k)
            headers[k] = v
        return self.post('', headers=headers)
    
    # Storage Container Services
    
    def list_objects(self, container, format='text', limit=None, marker=None,
                     prefix=None, delimiter=None, path=None,
                     include_trashed=False, params={}, if_modified_since=None,
                     if_unmodified_since=None, meta='', until=None):
        """returns a list with the container objects"""
        params = {'until':until, 'meta':meta}
        args = locals()
        for elem in ['self', 'container', 'params', 'until', 'meta']:
            args.pop(elem)
        return OOS_Client.list_objects(self, container, params=params, 
                                       **args)
    
    def retrieve_container_metadata(self, container, restricted=False,
                                    until=None):
        """returns container's metadata"""
        params = {'until':until} if until else {}
        return OOS_Client.retrieve_container_metadata(self, container,
                                                      restricted=restricted,
                                                      **params)
    
    def set_container_policies(self, container, **policies):
        """sets containers policies"""
        path = '/%s' % (container)
        headers = {}
        print ''
        for key, val in policies.items():
            headers['x-container-policy-%s' % key] = val
        return self.post(path, headers=headers)
    
    def delete_container(self, container, until=None):
        """deletes a container or the container history until the date provided"""
        params = {'until':until} if until else {}
        return OOS_Client.delete_container(self, container, params)
    
    # Storage Object Services
    
    def retrieve_object(self, container, object, params={}, format='text', range=None,
                        if_range=None, if_match=None, if_none_match=None,
                        if_modified_since=None, if_unmodified_since=None,
                        **headers):
        """returns an object"""
        headers={}
        l = ['range', 'if_range', 'if_match', 'if_none_match',
             'if_modified_since', 'if_unmodified_since']
        l = [elem for elem in l if eval(elem)]
        for elem in l:
            headers.update({elem:eval(elem)})
        return OOS_Client.retrieve_object(self, container, object, format=format,
                                          params=params, **headers)
    
    def retrieve_object_version(self, container, object, version, detail=False,
                                range=None, if_range=None, if_match=None,
                                if_none_match=None, if_modified_since=None,
                                if_unmodified_since=None):
        """returns a specific object version"""
        args = locals()
        l = ['self', 'container', 'object']
        for elem in l:
            args.pop(elem)
        params = {'version':version}
        return self.retrieve_object(container, object, params, **args)
    
    def retrieve_object_versionlist(self, container, object, range=None,
                                    if_range=None, if_match=None,
                                    if_none_match=None, if_modified_since=None,
                                    if_unmodified_since=None):
        """returns the object version list"""
        args = locals()
        l = ['self', 'container', 'object']
        for elem in l:
            args.pop(elem)
            
        return self.retrieve_object_version(container, object, version='list',
                                            detail=True, **args)
    
    def create_zero_length_object(self, container, object, meta={},
                      etag=None, content_type=None, content_encoding=None,
                      content_disposition=None, x_object_manifest=None,
                      x_object_sharing=None, x_object_public=None):
        """createas a zero length object"""
        args = locals()
        for elem in ['self', 'container', 'object']:
            args.pop(elem)
        return OOS_Client.create_zero_length_object(self, container, object,
                                                    **args)
    
    def create_object(self, container, object, f=stdin, meta={},
                      etag=None, content_type=None, content_encoding=None,
                      content_disposition=None, x_object_manifest=None,
                      x_object_sharing=None, x_object_public=None):
        """creates an object"""
        args = locals()
        for elem in ['self', 'container', 'object']:
            args.pop(elem)
        return OOS_Client.create_object(self, container, object, **args)
        
    def create_object_using_chunks(self, container, object, f=stdin,
                                    blocksize=1024, meta={}, etag=None,
                                    content_type=None, content_encoding=None,
                                    content_disposition=None, 
                                    x_object_sharing=None,
                                    x_object_manifest=None, 
                                    x_object_public=None):
        """creates an object (incremental upload)"""
        path = '/%s/%s' % (container, object)
        headers = {}
        l = ['etag', 'content_type', 'content_encoding', 'content_disposition', 
             'x_object_sharing', 'x_object_manifest', 'x_object_public']
        l = [elem for elem in l if eval(elem)]
        for elem in l:
            headers.update({elem:eval(elem)})
        
        for k,v in meta.items():
            v = v.strip()
            headers['x-object-meta-%s' %k.strip()] = v
        
        return self._chunked_transfer(path, 'PUT', f, headers=headers,
                                      blocksize=blocksize)
    
    def create_object_by_hashmap(container, object, f=stdin, format='json',
                                 meta={}, etag=None, content_encoding=None,
                                 content_disposition=None, content_type=None,
                                 x_object_sharing=None, x_object_manifest=None,
                                 x_object_public = None):
        """creates an object by uploading hashes representing data instead of data"""
        args = locals()
        for elem in ['self', 'container', 'object']:
            args.pop(elem)
            
        data = f.read() if f else None
        if data and format == 'json':
            try:
                data = eval(data)
                data = json.dumps(data)
            except SyntaxError:
                raise Fault('Invalid formatting')
        
        #TODO check with xml
        return self.create_object(container, object, **args)
    
    def create_manifestation(self, container, object, manifest):
        """creates a manifestation"""
        headers={'x_object_manifest':manifest}
        return self.create_object(container, object, f=None, **headers)
    
    def update_object(self, container, object, f=stdin, offset=None, meta={},
                      content_length=None, content_type=None, content_range=None,
                      content_encoding=None, content_disposition=None,
                      x_object_bytes=None, x_object_manifest=None,
                      x_object_sharing=None, x_object_public=None):
        """updates an object"""
        spath = '/%s/%s' % (container, object)
        args = locals()
        for elem in ['self', 'container', 'object']:
            args.pop(elem)
        
        return OOS_Client.update_object(self, container, object, **args)
        
    def update_object_using_chunks(self, container, object, f=stdin,
                                    blocksize=1024, offset=None, meta={},
                                    content_type=None, content_encoding=None,
                                    content_disposition=None, x_object_bytes=None,
                                    x_object_manifest=None, x_object_sharing=None,
                                    x_object_public=None):
        """updates an object (incremental upload)"""
        path = '/%s/%s' % (container, object)
        headers = {}
        l = ['content_type', 'content_encoding', 'content_disposition',
             'x_object_bytes', 'x_object_manifest', 'x_object_sharing',
             'x_object_public']
        l = [elem for elem in l if eval(elem)]
        for elem in l:
            headers.update({elem:eval(elem)})
        
        if offset != None:
            headers['content_range'] = 'bytes %s-/*' % offset
        else:
            headers['content_range'] = 'bytes */*'
        
        for k,v in meta.items():
            v = v.strip()
            headers['x-object-meta-%s' %k.strip()] = v
        
        return self._chunked_transfer(path, 'POST', f, headers=headers,
                                      blocksize=blocksize)
    
    def delete_object(self, container, object, until=None):
        """deletes an object or the object history until the date provided"""
        params = {'until':until} if until else {}
        return OOS_Client.delete_object(self, container, object, params)
    
    def trash_object(self, container, object):
        """trashes an object"""
        path = '/%s/%s' % (container, object)
        meta = {'trash':'true'}
        return self._update_metadata(path, 'object', **meta)
    
    def restore_object(self, container, object):
        """restores a trashed object"""
        return self.delete_object_metadata(container, object, ['trash'])
    
    def publish_object(self, container, object):
        """sets a previously created object publicly accessible"""
        path = '/%s/%s' % (container, object)
        headers = {'content_range':'bytes */*'}
        headers['x_object_public'] = True
        return self.post(path, headers=headers)
    
    def unpublish_object(self, container, object):
        """unpublish an object"""
        path = '/%s/%s' % (container, object)
        headers = {'content_range':'bytes */*'}
        headers['x_object_public'] = False
        return self.post(path, headers=headers)
    
    def _change_obj_location(self, src_container, src_object, dst_container,
                             dst_object, remove=False, meta={}, **headers):
        path = '/%s/%s' % (dst_container, dst_object)
        headers = {} if not headers else headers
        for k, v in meta.items():
            headers['x-object-meta-%s' % k] = v
        if remove:
            headers['x-move-from'] = '/%s/%s' % (src_container, src_object)
        else:
            headers['x-copy-from'] = '/%s/%s' % (src_container, src_object)
        headers['content_length'] = 0
        return self.put(path, headers=headers)
    
    def copy_object(self, src_container, src_object, dst_container, dst_object,
                    meta={}, public=False, version=None):
        """copies an object"""
        headers = {}
        headers['x_object_public'] = public
        if version:
            headers['x_object_version'] = version
        return OOS_Client.copy_object(self, src_container, src_object,
                                      dst_container, dst_object, meta=meta,
                                      **headers)
    
    def move_object(self, src_container, src_object, dst_container,
                             dst_object, meta={}, public=False, version=None):
        """moves an object"""
        headers = {}
        headers['x_object_public'] = public
        if version:
            headers['x_object_version'] = version
        return OOS_Client.move_object(self, src_container, src_object,
                                      dst_container, dst_object, meta=meta,
                                      **headers)
    
    def list_shared_by_others(self, limit=None, marker=None, format='text'):
         """lists other accounts that share objects to the user"""
         l = ['limit', 'marker']
         params = {}
         for elem in [elem for elem in l if eval(elem)]:
             params[elem] = eval(elem)
         return self._list('', format, params, top_level_req=True)
    
    def share_object(self, container, object, l, read=True):
        """gives access(read by default) to an object to a user/group list"""
        action = 'read' if read else 'write'
        sharing = '%s=%s' % (action, ','.join(l))
        self.update_object(container, object, f=None, x_object_sharing=sharing)

def _encode_headers(headers):
    h = {}
    for k, v in headers.items():
        k = urllib.quote(k)
        if v and type(v) == types.StringType:
            v = urllib.quote(v, '/=,-* :"')
        h[k] = v
    return h
