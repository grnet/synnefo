# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

from httplib import HTTPConnection, HTTPSConnection, HTTP
from sys import stdin
from xml.dom import minidom
from StringIO import StringIO
from urllib import quote, unquote
from urlparse import urlparse

import json
import types
import socket
import urllib
import datetime

ERROR_CODES = {304: 'Not Modified',
               400: 'Bad Request',
               401: 'Unauthorized',
               403: 'Forbidden',
               404: 'Not Found',
               409: 'Conflict',
               411: 'Length Required',
               412: 'Precondition Failed',
               413: 'Request Entity Too Large',
               416: 'Range Not Satisfiable',
               422: 'Unprocessable Entity',
               500: 'Internal Server Error',
               501: 'Not Implemented'}


class Fault(Exception):
    def __init__(self, data='', status=None):
        if data == '' and status in ERROR_CODES.keys():
            data = ERROR_CODES[status]
        Exception.__init__(self, data)
        self.data = data
        self.status = status


class Client(object):
    def __init__(self, url, token, account, verbose=False, debug=False):
        """`url` can also include a port, e.g '127.0.0.1:8000'."""

        self.url = url
        self.account = account
        self.verbose = verbose or debug
        self.debug = debug
        self.token = token

    def _req(self, method, path, body=None, headers={}, format='text', params={}):
        p = urlparse(self.url)
        if p.scheme == 'http':
            conn = HTTPConnection(p.netloc)
        elif p.scheme == 'https':
            conn = HTTPSConnection(p.netloc)
        else:
            raise Exception('Unknown URL scheme')

        full_path = _prepare_path(p.path + path, format, params)

        kwargs = {}
        kwargs['headers'] = _prepare_headers(headers)
        kwargs['headers']['X-Auth-Token'] = self.token
        if body:
            kwargs['body'] = body
            kwargs['headers'].setdefault(
                'content-type', 'application/octet-stream')
        kwargs['headers'].setdefault('content-length', len(body)
                                     if body else 0)

        #print '#', method, full_path, kwargs
        #t1 = datetime.datetime.utcnow()
        conn.request(method, full_path, **kwargs)

        resp = conn.getresponse()
        #t2 = datetime.datetime.utcnow()
        #print 'response time:', str(t2-t1)
        return _handle_response(resp, self.verbose, self.debug)

    def _chunked_transfer(self, path, method='PUT', f=stdin, headers=None,
                          blocksize=1024, params={}):
        """perfomrs a chunked request"""
        p = urlparse(self.url)
        if p.scheme == 'http':
            conn = HTTPConnection(p.netloc)
        elif p.scheme == 'https':
            conn = HTTPSConnection(p.netloc)
        else:
            raise Exception('Unknown URL scheme')

        full_path = _prepare_path(p.path + path, params=params)

        headers.setdefault('content-type', 'application/octet-stream')

        conn.putrequest(method, full_path)
        conn.putheader('x-auth-token', self.token)
        conn.putheader('transfer-encoding', 'chunked')
        for k, v in _prepare_headers(headers).items():
            conn.putheader(k, v)
        conn.endheaders()

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
                conn.send(data)
            except:
                #retry
                conn.send(data)
        data = '0\r\n\r\n'
        try:
            conn.send(data)
        except:
            #retry
            conn.send(data)

        resp = conn.getresponse()
        return _handle_response(resp, self.verbose, self.debug)

    def delete(self, path, format='text', params={}):
        return self._req('DELETE', path, format=format, params=params)

    def get(self, path, format='text', headers={}, params={}):
        return self._req('GET', path, headers=headers, format=format,
                         params=params)

    def head(self, path, format='text', params={}):
        return self._req('HEAD', path, format=format, params=params)

    def post(self, path, body=None, format='text', headers=None, params={}):
        return self._req('POST', path, body, headers=headers, format=format,
                         params=params)

    def put(self, path, body=None, format='text', headers=None, params={}):
        return self._req('PUT', path, body, headers=headers, format=format,
                         params=params)

    def _list(self, path, format='text', params={}, **headers):
        status, headers, data = self.get(path, format=format, headers=headers,
                                         params=params)
        if format == 'json':
            data = json.loads(data) if data else ''
        elif format == 'xml':
            data = minidom.parseString(data)
        else:
            data = data.split('\n')[:-1] if data else ''
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
            if isinstance(elem, types.DictionaryType):
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
        for k, v in ex_meta.items():
            k = '%s%s' % (prefix, k)
            headers[k] = v
        return self.post(path, headers=headers)

    def _reset_metadata(self, path, entity, **meta):
        """
        overwrites all user defined metadata
        """
        headers = {}
        prefix = 'x-%s-meta-' % entity
        for k, v in meta.items():
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

    def list_containers(self, format='text', limit=None,
                        marker=None, params={}, account=None, **headers):
        """lists containers"""
        account = account or self.account
        path = '/%s' % account
        params.update({'limit': limit, 'marker': marker})
        return self._list(path, format, params, **headers)

    def retrieve_account_metadata(self, restricted=False, account=None, **params):
        """returns the account metadata"""
        account = account or self.account
        path = '/%s' % account
        prefix = 'x-account-meta-' if restricted else None
        return self._get_metadata(path, prefix, params)

    def update_account_metadata(self, account=None, **meta):
        """updates the account metadata"""
        account = account or self.account
        path = '/%s' % account
        return self._update_metadata(path, 'account', **meta)

    def delete_account_metadata(self, meta=[], account=None):
        """deletes the account metadata"""
        account = account or self.account
        path = '/%s' % account
        return self._delete_metadata(path, 'account', meta)

    def reset_account_metadata(self, account=None, **meta):
        """resets account metadata"""
        account = account or self.account
        path = '/%s' % account
        return self._reset_metadata(path, 'account', **meta)

    # Storage Container Services

    def _filter_trashed(self, l):
        return self._filter(l, {'trash': 'true'})

    def list_objects(self, container, format='text',
                     limit=None, marker=None, prefix=None, delimiter=None,
                     path=None, include_trashed=False, params={}, account=None,
                     **headers):
        """returns a list with the container objects"""
        account = account or self.account
        params.update({'limit': limit, 'marker': marker, 'prefix': prefix,
                       'delimiter': delimiter, 'path': path})
        l = self._list('/%s/%s' % (account, container), format, params,
                       **headers)
        #TODO support filter trashed with xml also
        if format != 'xml' and not include_trashed:
            l = self._filter_trashed(l)
        return l

    def create_container(self, container, account=None, meta={}, **headers):
        """creates a container"""
        account = account or self.account
        if not headers:
            headers = {}
        for k, v in meta.items():
            headers['x-container-meta-%s' % k.strip().upper()] = v.strip()
        status, header, data = self.put('/%s/%s' % (account, container),
                                        headers=headers)
        if status == 202:
            return False
        elif status != 201:
            raise Fault(data, int(status))
        return True

    def delete_container(self, container, params={}, account=None):
        """deletes a container"""
        account = account or self.account
        return self.delete('/%s/%s' % (account, container), params=params)

    def retrieve_container_metadata(self, container, restricted=False,
                                    account=None, **params):
        """returns the container metadata"""
        account = account or self.account
        prefix = 'x-container-meta-' if restricted else None
        return self._get_metadata('/%s/%s' % (account, container), prefix,
                                  params)

    def update_container_metadata(self, container, account=None, **meta):
        """unpdates the container metadata"""
        account = account or self.account
        return self._update_metadata('/%s/%s' % (account, container),
                                     'container', **meta)

    def delete_container_metadata(self, container, meta=[], account=None):
        """deletes the container metadata"""
        account = account or self.account
        path = '/%s/%s' % (account, container)
        return self._delete_metadata(path, 'container', meta)

    # Storage Object Services

    def request_object(self, container, object, format='text', params={},
                       account=None, **headers):
        """returns tuple containing the status, headers and data response for an object request"""
        account = account or self.account
        path = '/%s/%s/%s' % (account, container, object)
        status, headers, data = self.get(path, format, headers, params)
        return status, headers, data

    def retrieve_object(self, container, object, format='text', params={},
                        account=None, **headers):
        """returns an object's data"""
        account = account or self.account
        t = self.request_object(container, object, format, params, account,
                                **headers)
        data = t[2]
        if format == 'json':
            data = json.loads(data) if data else ''
        elif format == 'xml':
            data = minidom.parseString(data)
        return data

    def retrieve_object_hashmap(
        self, container, object, format='json', params={},
            account=None, **headers):
        """returns the hashmap representing object's data"""
        if not params:
            params = {}
        params.update({'hashmap': None})
        return self.retrieve_object(container, object, params, format, account, **headers)

    def create_directory_marker(self, container, object, account=None):
        """creates a dierectory marker"""
        account = account or self.account
        if not object:
            raise Fault('Directory markers have to be nested in a container')
        h = {'content_type': 'application/directory'}
        return self.create_zero_length_object(
            container, object, account=account,
            **h)

    def create_object(self, container, object, f=stdin, format='text', meta={},
                      params={}, etag=None, content_type=None, content_encoding=None,
                      content_disposition=None, account=None, **headers):
        """creates a zero-length object"""
        account = account or self.account
        path = '/%s/%s/%s' % (account, container, object)
        for k, v in headers.items():
            if v is None:
                headers.pop(k)

        l = ['etag', 'content_encoding', 'content_disposition', 'content_type']
        l = [elem for elem in l if eval(elem)]
        for elem in l:
            headers.update({elem: eval(elem)})
        headers.setdefault('content-type', 'application/octet-stream')

        for k, v in meta.items():
            headers['x-object-meta-%s' % k.strip()] = v.strip()
        data = f.read() if f else None
        return self.put(path, data, format, headers=headers, params=params)

    def create_zero_length_object(self, container, object, meta={}, etag=None,
                                  content_type=None, content_encoding=None,
                                  content_disposition=None, account=None,
                                  **headers):
        account = account or self.account
        args = locals().copy()
        for elem in ['self', 'container', 'headers', 'account']:
            args.pop(elem)
        args.update(headers)
        return self.create_object(container, account=account, f=None, **args)

    def update_object(self, container, object, f=stdin,
                      offset=None, meta={}, params={}, content_length=None,
                      content_type=None, content_encoding=None,
                      content_disposition=None, account=None, **headers):
        account = account or self.account
        path = '/%s/%s/%s' % (account, container, object)
        for k, v in headers.items():
            if v is None:
                headers.pop(k)

        l = ['content_encoding', 'content_disposition', 'content_type',
             'content_length']
        l = [elem for elem in l if eval(elem)]
        for elem in l:
            headers.update({elem: eval(elem)})

        if 'content_range' not in headers.keys():
            if offset is not None:
                headers['content_range'] = 'bytes %s-/*' % offset
            else:
                headers['content_range'] = 'bytes */*'

        for k, v in meta.items():
            headers['x-object-meta-%s' % k.strip()] = v.strip()
        data = f.read() if f else None
        return self.post(path, data, headers=headers, params=params)

    def update_object_using_chunks(self, container, object, f=stdin,
                                   blocksize=1024, offset=None, meta={},
                                   params={}, content_type=None, content_encoding=None,
                                   content_disposition=None, account=None, **headers):
        """updates an object (incremental upload)"""
        account = account or self.account
        path = '/%s/%s/%s' % (account, container, object)
        headers = headers if not headers else {}
        l = ['content_type', 'content_encoding', 'content_disposition']
        l = [elem for elem in l if eval(elem)]
        for elem in l:
            headers.update({elem: eval(elem)})

        if offset is not None:
            headers['content_range'] = 'bytes %s-/*' % offset
        else:
            headers['content_range'] = 'bytes */*'

        for k, v in meta.items():
            v = v.strip()
            headers['x-object-meta-%s' % k.strip()] = v
        return self._chunked_transfer(path, 'POST', f, headers=headers,
                                      blocksize=blocksize, params=params)

    def _change_obj_location(self, src_container, src_object, dst_container,
                             dst_object, remove=False, meta={}, account=None,
                             content_type=None, delimiter=None, **headers):
        account = account or self.account
        path = '/%s/%s/%s' % (account, dst_container, dst_object)
        headers = {} if not headers else headers
        params = {}
        for k, v in meta.items():
            headers['x-object-meta-%s' % k] = v
        if remove:
            headers['x-move-from'] = '/%s/%s' % (src_container, src_object)
        else:
            headers['x-copy-from'] = '/%s/%s' % (src_container, src_object)
        headers['content_length'] = 0
        if content_type:
            headers['content_type'] = content_type
        else:
            params['ignore_content_type'] = ''
        if delimiter:
            params['delimiter'] = delimiter
        return self.put(path, headers=headers, params=params)

    def copy_object(self, src_container, src_object, dst_container, dst_object,
                    meta={}, account=None, content_type=None, delimiter=None, **headers):
        """copies an object"""
        account = account or self.account
        return self._change_obj_location(src_container, src_object,
                                         dst_container, dst_object, account=account,
                                         remove=False, meta=meta,
                                         content_type=content_type, delimiter=delimiter, **headers)

    def move_object(self, src_container, src_object, dst_container,
                    dst_object, meta={}, account=None,
                    content_type=None, **headers):
        """moves an object"""
        account = account or self.account
        return self._change_obj_location(src_container, src_object,
                                         dst_container, dst_object,
                                         account=account, remove=True,
                                         meta=meta, content_type=content_type,
                                         **headers)

    def delete_object(self, container, object, params={}, account=None):
        """deletes an object"""
        account = account or self.account
        return self.delete('/%s/%s/%s' % (account, container, object),
                           params=params)

    def retrieve_object_metadata(self, container, object, restricted=False,
                                 version=None, account=None):
        """
        set restricted to True to get only user defined metadata
        """
        account = account or self.account
        path = '/%s/%s/%s' % (account, container, object)
        prefix = 'x-object-meta-' if restricted else None
        params = {'version': version} if version else {}
        return self._get_metadata(path, prefix, params=params)

    def update_object_metadata(self, container, object, account=None,
                               **meta):
        """
        updates object's metadata
        """
        account = account or self.account
        path = '/%s/%s/%s' % (account, container, object)
        return self._update_metadata(path, 'object', **meta)

    def delete_object_metadata(self, container, object, meta=[], account=None):
        """
        deletes object's metadata
        """
        account = account or self.account
        path = '/%s/%s' % (account, container, object)
        return self._delete_metadata(path, 'object', meta)


class Pithos_Client(OOS_Client):
    """Pithos Storage Client. Extends OOS_Client"""

    def _update_metadata(self, path, entity, **meta):
        """
        adds new and updates the values of previously set metadata
        """
        params = {'update': None}
        headers = {}
        prefix = 'x-%s-meta-' % entity
        for k, v in meta.items():
            k = '%s%s' % (prefix, k)
            headers[k] = v
        return self.post(path, headers=headers, params=params)

    def _delete_metadata(self, path, entity, meta=[]):
        """
        delete previously set metadata
        """
        params = {'update': None}
        headers = {}
        prefix = 'x-%s-meta-' % entity
        for m in meta:
            headers['%s%s' % (prefix, m)] = ''
        return self.post(path, headers=headers, params=params)

    # Storage Account Services

    def list_containers(self, format='text', if_modified_since=None,
                        if_unmodified_since=None, limit=None, marker=None,
                        shared=False, until=None, account=None, public=False):
        """returns a list with the account containers"""
        account = account or self.account
        params = {'until': until} if until else {}
        if shared:
            params['shared'] = None
        if public:
            params['public'] = None
        headers = {'if-modified-since': if_modified_since,
                   'if-unmodified-since': if_unmodified_since}
        return OOS_Client.list_containers(self, account=account, format=format,
                                          limit=limit, marker=marker,
                                          params=params, **headers)

    def retrieve_account_metadata(self, restricted=False, until=None,
                                  account=None):
        """returns the account metadata"""
        account = account or self.account
        params = {'until': until} if until else {}
        return OOS_Client.retrieve_account_metadata(self, account=account,
                                                    restricted=restricted,
                                                    **params)

    def set_account_groups(self, account=None, **groups):
        """create account groups"""
        account = account or self.account
        path = '/%s' % account
        headers = {}
        for k, v in groups.items():
            headers['x-account-group-%s' % k] = v
        params = {'update': None}
        return self.post(path, headers=headers, params=params)

    def retrieve_account_groups(self, account=None):
        """returns the account groups"""
        account = account or self.account
        meta = self.retrieve_account_metadata(account=account)
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

    def unset_account_groups(self, groups=[], account=None):
        """delete account groups"""
        account = account or self.account
        path = '/%s' % account
        headers = {}
        for elem in groups:
            headers['x-account-group-%s' % elem] = ''
        params = {'update': None}
        return self.post(path, headers=headers, params=params)

    def reset_account_groups(self, account=None, **groups):
        """overrides account groups"""
        account = account or self.account
        path = '/%s' % account
        headers = {}
        for k, v in groups.items():
            v = v.strip()
            headers['x-account-group-%s' % k] = v
        meta = self.retrieve_account_metadata(restricted=True)
        prefix = 'x-account-meta-'
        for k, v in meta.items():
            k = '%s%s' % (prefix, k)
            headers[k] = v
        return self.post(path, headers=headers)

    # Storage Container Services
    def create_container(self, container, account=None, meta={}, policies={}):
        """creates a container"""
        args = {}
        for k, v in policies.items():
            args['X-Container-Policy-%s' % k.capitalize()] = v
        return OOS_Client.create_container(self, container, account, meta, **args)

    def list_objects(self, container, format='text',
                     limit=None, marker=None, prefix=None, delimiter=None,
                     path=None, shared=False, include_trashed=False, params={},
                     if_modified_since=None, if_unmodified_since=None, meta='',
                     until=None, account=None, public=False):
        """returns a list with the container objects"""
        account = account or self.account
        params = {'until': until, 'meta': meta}
        if shared:
            params['shared'] = None
        if public:
            params['public'] = None
        args = locals().copy()
        for elem in ['self', 'container', 'params', 'until', 'meta']:
            args.pop(elem)
        return OOS_Client.list_objects(self, container, params=params, **args)

    def retrieve_container_metadata(self, container, restricted=False,
                                    until=None, account=None):
        """returns container's metadata"""
        account = account or self.account
        params = {'until': until} if until else {}
        return OOS_Client.retrieve_container_metadata(self, container,
                                                      account=account,
                                                      restricted=restricted,
                                                      **params)

    def set_container_policies(self, container, account=None,
                               **policies):
        """sets containers policies"""
        account = account or self.account
        path = '/%s/%s' % (account, container)
        headers = {}
        for key, val in policies.items():
            headers['x-container-policy-%s' % key] = val
        return self.post(path, headers=headers)

    def update_container_data(self, container, f=stdin):
        """adds blocks of data to the container"""
        account = self.account
        path = '/%s/%s' % (account, container)
        params = {'update': None}
        headers = {'content_type': 'application/octet-stream'}
        data = f.read() if f else None
        headers['content_length'] = len(data)
        return self.post(path, data, headers=headers, params=params)

    def delete_container(self, container, until=None, account=None, delimiter=None):
        """deletes a container or the container history until the date provided"""
        account = account or self.account
        params = {'until': until} if until else {}
        if delimiter:
            params['delimiter'] = delimiter
        return OOS_Client.delete_container(self, container, account=account,
                                           params=params)

    # Storage Object Services

    def retrieve_object(self, container, object, params={}, format='text',
                        range=None, if_range=None,
                        if_match=None, if_none_match=None,
                        if_modified_since=None, if_unmodified_since=None,
                        account=None, **headers):
        """returns an object"""
        account = account or self.account
        headers = {}
        l = ['range', 'if_range', 'if_match', 'if_none_match',
             'if_modified_since', 'if_unmodified_since']
        l = [elem for elem in l if eval(elem)]
        for elem in l:
            headers.update({elem: eval(elem)})
        if format != 'text':
            params['hashmap'] = None
        return OOS_Client.retrieve_object(self, container, object,
                                          account=account, format=format,
                                          params=params, **headers)

    def retrieve_object_version(self, container, object, version,
                                format='text', range=None, if_range=None,
                                if_match=None, if_none_match=None,
                                if_modified_since=None, if_unmodified_since=None,
                                account=None):
        """returns a specific object version"""
        account = account or self.account
        args = locals().copy()
        l = ['self', 'container', 'object']
        for elem in l:
            args.pop(elem)
        params = {'version': version}
        return self.retrieve_object(container, object, params=params, **args)

    def retrieve_object_versionlist(self, container, object, range=None,
                                    if_range=None, if_match=None,
                                    if_none_match=None, if_modified_since=None,
                                    if_unmodified_since=None, account=None):
        """returns the object version list"""
        account = account or self.account
        args = locals().copy()
        l = ['self', 'container', 'object']
        for elem in l:
            args.pop(elem)

        return self.retrieve_object_version(container, object, version='list',
                                            format='json', **args)

    def create_zero_length_object(self, container, object,
                                  meta={}, etag=None, content_type=None,
                                  content_encoding=None,
                                  content_disposition=None,
                                  x_object_manifest=None, x_object_sharing=None,
                                  x_object_public=None, account=None):
        """createas a zero length object"""
        account = account or self.account
        args = locals().copy()
        for elem in ['self', 'container', 'object']:
            args.pop(elem)
        return OOS_Client.create_zero_length_object(self, container, object,
                                                    **args)

    def create_folder(self, container, name,
                      meta={}, etag=None,
                      content_encoding=None,
                      content_disposition=None,
                      x_object_manifest=None, x_object_sharing=None,
                      x_object_public=None, account=None):
        args = locals().copy()
        for elem in ['self', 'container', 'name']:
            args.pop(elem)
        args['content_type'] = 'application/directory'
        return self.create_zero_length_object(container, name, **args)

    def create_object(self, container, object, f=stdin, format='text',
                      meta={}, params={}, etag=None, content_type=None,
                      content_encoding=None, content_disposition=None,
                      x_object_manifest=None, x_object_sharing=None,
                      x_object_public=None, account=None):
        """creates an object"""
        account = account or self.account
        args = locals().copy()
        for elem in ['self', 'container', 'object']:
            args.pop(elem)
        if format != 'text':
            params.update({'hashmap': None})
        return OOS_Client.create_object(self, container, object, **args)

    def create_object_using_chunks(self, container, object,
                                   f=stdin, blocksize=1024, meta={}, etag=None,
                                   content_type=None, content_encoding=None,
                                   content_disposition=None,
                                   x_object_sharing=None, x_object_manifest=None,
                                   x_object_public=None, account=None):
        """creates an object (incremental upload)"""
        account = account or self.account
        path = '/%s/%s/%s' % (account, container, object)
        headers = {}
        l = ['etag', 'content_type', 'content_encoding', 'content_disposition',
             'x_object_sharing', 'x_object_manifest', 'x_object_public']
        l = [elem for elem in l if eval(elem)]
        for elem in l:
            headers.update({elem: eval(elem)})
        headers.setdefault('content-type', 'application/octet-stream')

        for k, v in meta.items():
            v = v.strip()
            headers['x-object-meta-%s' % k.strip()] = v

        return self._chunked_transfer(path, 'PUT', f, headers=headers,
                                      blocksize=blocksize)

    def create_object_by_hashmap(self, container, object, hashmap={},
                                 meta={}, etag=None, content_encoding=None,
                                 content_disposition=None, content_type=None,
                                 x_object_sharing=None, x_object_manifest=None,
                                 x_object_public=None, account=None):
        """creates an object by uploading hashes representing data instead of data"""
        account = account or self.account
        args = locals().copy()
        for elem in ['self', 'container', 'object', 'hashmap']:
            args.pop(elem)

        try:
            data = json.dumps(hashmap)
        except SyntaxError:
            raise Fault('Invalid formatting')
        args['params'] = {'hashmap': None}
        args['format'] = 'json'

        return self.create_object(container, object, f=StringIO(data), **args)

    def create_manifestation(self, container, object, manifest, account=None):
        """creates a manifestation"""
        account = account or self.account
        headers = {'x_object_manifest': manifest}
        return self.create_object(container, object, f=None, account=account,
                                  **headers)

    def update_object(self, container, object, f=stdin,
                      offset=None, meta={}, replace=False, content_length=None,
                      content_type=None, content_range=None,
                      content_encoding=None, content_disposition=None,
                      x_object_bytes=None, x_object_manifest=None,
                      x_object_sharing=None, x_object_public=None,
                      x_source_object=None, account=None):
        """updates an object"""
        account = account or self.account
        args = locals().copy()
        for elem in ['self', 'container', 'object', 'replace']:
            args.pop(elem)
        if not replace:
            args['params'] = {'update': None}
        return OOS_Client.update_object(self, container, object, **args)

    def update_object_using_chunks(self, container, object, f=stdin,
                                   blocksize=1024, offset=None, meta={},
                                   replace=False, content_type=None, content_encoding=None,
                                   content_disposition=None, x_object_bytes=None,
                                   x_object_manifest=None, x_object_sharing=None,
                                   x_object_public=None, account=None):
        """updates an object (incremental upload)"""
        account = account or self.account
        args = locals().copy()
        for elem in ['self', 'container', 'object', 'replace']:
            args.pop(elem)
        if not replace:
            args['params'] = {'update': None}
        return OOS_Client.update_object_using_chunks(self, container, object, **args)

    def update_from_other_source(self, container, object, source,
                                 offset=None, meta={}, content_range=None,
                                 content_encoding=None, content_disposition=None,
                                 x_object_bytes=None, x_object_manifest=None,
                                 x_object_sharing=None, x_object_public=None, account=None):
        """updates an object"""
        account = account or self.account
        args = locals().copy()
        for elem in ['self', 'container', 'object', 'source']:
            args.pop(elem)

        args['x_source_object'] = source
        return self.update_object(container, object, f=None, **args)

    def delete_object(self, container, object, until=None, account=None, delimiter=None):
        """deletes an object or the object history until the date provided"""
        account = account or self.account
        params = {'until': until} if until else {}
        if delimiter:
            params['delimiter'] = delimiter
        return OOS_Client.delete_object(self, container, object, params, account)

    def trash_object(self, container, object):
        """trashes an object"""
        account = account or self.account
        path = '/%s/%s' % (container, object)
        meta = {'trash': 'true'}
        return self._update_metadata(path, 'object', **meta)

    def restore_object(self, container, object, account=None):
        """restores a trashed object"""
        account = account or self.account
        return self.delete_object_metadata(container, object, account, ['trash'])

    def publish_object(self, container, object, account=None):
        """sets a previously created object publicly accessible"""
        account = account or self.account
        path = '/%s/%s/%s' % (account, container, object)
        headers = {}
        headers['x_object_public'] = True
        params = {'update': None}
        return self.post(path, headers=headers, params=params)

    def unpublish_object(self, container, object, account=None):
        """unpublish an object"""
        account = account or self.account
        path = '/%s/%s/%s' % (account, container, object)
        headers = {}
        headers['x_object_public'] = False
        params = {'update': None}
        return self.post(path, headers=headers, params=params)

    def copy_object(self, src_container, src_object, dst_container, dst_object,
                    meta={}, public=False, version=None, account=None,
                    content_type=None, delimiter=None):
        """copies an object"""
        account = account or self.account
        headers = {}
        headers['x_object_public'] = public
        if version:
            headers['x_source_version'] = version
        return OOS_Client.copy_object(self, src_container, src_object,
                                      dst_container, dst_object, meta=meta,
                                      account=account, content_type=content_type,
                                      delimiter=delimiter,
                                      **headers)

    def move_object(self, src_container, src_object, dst_container,
                    dst_object, meta={}, public=False,
                    account=None, content_type=None, delimiter=None):
        """moves an object"""
        headers = {}
        headers['x_object_public'] = public
        return OOS_Client.move_object(self, src_container, src_object,
                                      dst_container, dst_object, meta=meta,
                                      account=account, content_type=content_type,
                                      delimiter=delimiter,
                                      **headers)

    def list_shared_by_others(self, limit=None, marker=None, format='text'):
        """lists other accounts that share objects to the user"""
        l = ['limit', 'marker']
        params = {}
        for elem in [elem for elem in l if eval(elem)]:
            params[elem] = eval(elem)
        return self._list('', format, params)

    def share_object(self, container, object, l, read=True):
        """gives access(read by default) to an object to a user/group list"""
        action = 'read' if read else 'write'
        sharing = '%s=%s' % (action, ','.join(l))
        self.update_object(container, object, f=None, x_object_sharing=sharing)


def _prepare_path(path, format='text', params={}):
    full_path = '%s?format=%s' % (quote(path), format)

    for k, v in params.items():
        value = quote(str(v)) if v else ''
        full_path = '%s&%s=%s' % (full_path, quote(k), value)
    return full_path


def _prepare_headers(headers):
    for k, v in headers.items():
        headers.pop(k)
        k = k.replace('_', '-')
        headers[quote(k)] = quote(
            v, safe='/=,:@ *"') if isinstance(v, types.StringType) else v
    return headers


def _handle_response(response, verbose=False, debug=False):
    headers = response.getheaders()
    headers = dict((unquote(h), unquote(v)) for h, v in headers)

    if verbose:
        print '%d %s' % (response.status, response.reason)
        for key, val in headers.items():
            print '%s: %s' % (key.capitalize(), val)
        print

    length = response.getheader('content-length', None)
    data = response.read(length)
    if debug:
        print data
        print

    if int(response.status) in ERROR_CODES.keys():
        raise Fault(data, int(response.status))

    #print '**',  response.status, headers, data, '\n'
    return response.status, headers, data
