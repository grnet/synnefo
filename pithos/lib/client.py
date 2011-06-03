from httplib import HTTPConnection

import json

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
    
    def req(self, method, path, body=None, headers=None, format='text', params=None):
        full_path = '/%s/%s%s?format=%s' % (self.api, self.account, path, format)
        if params:
            for k,v in params.items():
                full_path = '%s&%s=%s' %(full_path, k, v)
        conn = HTTPConnection(self.host)
        
        kwargs = {}
        kwargs['headers'] = headers or {}
        kwargs['headers']['Content-Length'] = len(body) if body else 0
        if body:
            kwargs['body'] = body
            kwargs['headers']['Content-Type'] = 'application/octet-stream'
        
        conn.request(method, full_path, params, **kwargs)
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
        
        if format == 'json':
            data = json.loads(data)
        
        return resp.status, headers, data
    
    def delete(self, path, format='text'):
        return self.req('DELETE', path, format=format)
    
    def get(self, path, format='text', headers=None, params=None):
        return self.req('GET', path, headers=headers, format=format,
                        params=None)
    
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
        return data
    
    def _get_metadata(self, path, prefix):
        status, headers, data = self.head(path)
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
    
    def list_containers(self, detail=False, limit=1000, marker=None,
                        if_modified_since=None, if_unmodified_since=None):
        d = {}
        if if_modified_since:
            d['IF_MODIFIED_SINCE'] = if_modified_since
        if if_unmodified_since:
            d['IF_UNMODIFIED_SINCE'] = if_unmodified_since
        headers = d and d or None
        params = {'limit':limit, 'marker':marker}
        return self._list('', detail, params, headers)
    
    def account_metadata(self):
        return self._get_metadata('', 'x-account-')

    def update_account_metadata(self, **meta):
        self._set_metadata('', 'account', **meta)
    
    # Storage Container Services
    
    def list_objects(self, container, detail=False, limit=1000, marker=None,
                     prefix=None, delimiter=None, path=None, meta=None,
                     if_modified_since=None, if_unmodified_since=None):
        params = locals()
        params.pop('container')
        params.pop('detail')
        return self._list('/' + container, detail)
    
    def create_container(self, container):
        status, header, data = self.put('/' + container)
        if status == 202:
            return False
        elif status != 201:
            raise Fault(data)
        return True
    
    def delete_container(self, container):
        self.delete('/' + container)
    
    def retrieve_container_metadata(self, container):
        return self._get_metadata('/%s' % container, 'x-container-')

    def update_container_metadata(self, container, **meta):
        self._set_metadata('/' + container, 'container', **meta)
    
    # Storage Object Services
    
    def retrieve_object(self, container, object):
        path = '/%s/%s' % (container, object)
        status, headers, data = self.get(path)
        return data
    
    def create_object(self, container, object, data):
        path = '/%s/%s' % (container, object)
        self.put(path, data)
    
    def copy_object(self, src_container, src_object, dst_container, dst_object):
        path = '/%s/%s' % (dst_container, dst_object)
        headers = {}
        headers['X-Copy-From'] = '/%s/%s' % (src_container, src_object)
        headers['Content-Length'] = 0
        self.put(path, headers=headers)
    
    def delete_object(self, container, object):
        self.delete('/%s/%s' % (container, object))
    
    def retrieve_object_metadata(self, container, object):
        path = '/%s/%s' % (container, object)
        return self._get_metadata(path, 'x-object-meta-')
    
    def update_object_metadata(self, container, object, **meta):
        path = '/%s/%s' % (container, object)
        self._set_metadata(path, 'object', **meta)
