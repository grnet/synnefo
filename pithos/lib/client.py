from httplib import HTTPConnection, HTTP
from sys import stdin

import json
import types

class Fault(Exception):
    def __init__(self, data=''):
        Exception.__init__(self, data)
        self.data = data


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
        
        data = resp.read()
        if self.debug:
            print data
            print
        
        return resp.status, headers, data

    def req(self, method, path, body=None, headers=None, format='text', params=None):
        full_path = '/%s/%s%s?format=%s' % (self.api, self.account, path, format)
        if params:
            for k,v in params.items():
                if v:
                    full_path = '%s&%s=%s' %(full_path, k, v)
        conn = HTTPConnection(self.host)
        
        
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
        conn.request(method, full_path, **kwargs)
        resp = conn.getresponse()
        headers = dict(resp.getheaders())
        
        if self.verbose:
            print '%d %s' % (resp.status, resp.reason)
            for key, val in headers.items():
                print '%s: %s' % (key.capitalize(), val)
            print
        
        data = resp.read()
        if self.debug:
            print data
            print
        
        return resp.status, headers, data

    def delete(self, path, format='text'):
        return self.req('DELETE', path, format=format)

    def get(self, path, format='text', headers=None, params=None):
        return self.req('GET', path, headers=headers, format=format,
                        params=params)

    def head(self, path, format='text'):
        return self.req('HEAD', path, format=format)

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
            data = [data]
        return data

    def _get_metadata(self, path, prefix):
        status, headers, data = self.head(path)
        if status == '404':
            return None
        prefixlen = len(prefix)
        meta = {}
        for key, val in headers.items():
            if key.startswith(prefix):
                key = key[prefixlen:]
                meta[key] = val
        return meta

    def _set_metadata(self, path, entity, **meta):
        headers = {}
        for key, val in meta.items():
            http_key = 'X-%s-Meta-%s' %(entity.capitalize(), key.capitalize())
            headers[http_key] = val
        self.post(path, headers=headers)

    # Storage Account Services

    def list_containers(self, detail=False, params=None, headers=None):
        return self._list('', detail, params, headers)

    def account_metadata(self):
        return self._get_metadata('', 'x-account-meta-')

    def update_account_metadata(self, **meta):
        self._set_metadata('', 'account', **meta)

    # Storage Container Services

    def list_objects(self, container, detail=False, params=None, headers=None):
        return self._list('/' + container, detail, params, headers)

    def create_container(self, container, headers=None):
        status, header, data = self.put('/' + container, headers=headers)
        if status == 202:
            return False
        elif status != 201:
            raise Fault(data)
        return True

    def delete_container(self, container):
        self.delete('/' + container)

    def retrieve_container_metadata(self, container):
        return self._get_metadata('/%s' % container, 'x-container-meta-')

    def update_container_metadata(self, container, **meta):
        self._set_metadata('/' + container, 'container', **meta)

    # Storage Object Services

    def retrieve_object(self, container, object, detail=False, headers=None):
        path = '/%s/%s' % (container, object)
        format = 'json' if detail else 'text'
        status, headers, data = self.get(path, format, headers)
        return data

    def create_object(self, container, object, f=stdin, chunked=False,
                      blocksize=1024, headers=None):
        if not f:
            return
        path = '/%s/%s' % (container, object)
        if not chunked and f != stdin:
            data = f.read()
            self.put(path, data, headers=headers)
        else:
            self._chunked_transfer(path, 'PUT', f, headers=headers,
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
                             dst_object, remove=False):
        path = '/%s/%s' % (dst_container, dst_object)
        headers = {}
        if remove:
            headers['X-Move-From'] = '/%s/%s' % (src_container, src_object)
        else:
            headers['X-Copy-From'] = '/%s/%s' % (src_container, src_object)
        headers['Content-Length'] = 0
        self.put(path, headers=headers)

    def copy_object(self, src_container, src_object, dst_container,
                             dst_object):
        self._change_obj_location(src_container, src_object,
                                   dst_container, dst_object)

    def move_object(self, src_container, src_object, dst_container,
                             dst_object):
        self._change_obj_location(src_container, src_object,
                                   dst_container, dst_object, True)

    def delete_object(self, container, object):
        self.delete('/%s/%s' % (container, object))

    def retrieve_object_metadata(self, container, object):
        path = '/%s/%s' % (container, object)
        return self._get_metadata(path, 'x-object-meta-')

    def update_object_metadata(self, container, object, **meta):
        path = '/%s/%s' % (container, object)
        self._set_metadata(path, 'object', **meta)
