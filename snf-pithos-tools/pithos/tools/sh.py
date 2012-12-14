#!/usr/bin/env python

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

from getpass import getuser
from optparse import OptionParser
from os import environ
from sys import argv, exit, stdin, stdout
from datetime import datetime

from pithos.tools.lib.client import Pithos_Client, Fault
from pithos.tools.lib.util import get_user, get_auth, get_url
from pithos.tools.lib.transfer import upload, download

import json
import logging
import types
import re
import time as _time
import os

_cli_commands = {}


def cli_command(*args):
    def decorator(cls):
        cls.commands = args
        for name in args:
            _cli_commands[name] = cls
        return cls
    return decorator


def class_for_cli_command(name):
    return _cli_commands[name]


class Command(object):
    syntax = ''

    def __init__(self, name, argv):
        parser = OptionParser('%%prog %s [options] %s' % (name, self.syntax))
        parser.add_option('--url', dest='url', metavar='URL',
                          default=get_url(), help='server URL (currently: %s)' % get_url())
        parser.add_option('--user', dest='user', metavar='USER',
                          default=get_user(),
                          help='account USER (currently: %s)' % get_user())
        parser.add_option('--token', dest='token', metavar='TOKEN',
                          default=get_auth(),
                          help='account TOKEN (currently: %s)' % get_auth())
        parser.add_option('-v', action='store_true', dest='verbose',
                          default=False, help='verbose output')
        parser.add_option('-d', action='store_true', dest='debug',
                          default=False, help='debug output')
        self.add_options(parser)
        options, args = parser.parse_args(argv)

        # Add options to self
        for opt in parser.option_list:
            key = opt.dest
            if key:
                val = getattr(options, key)
                setattr(self, key, val)

        self.client = Pithos_Client(
            self.url, self.token, self.user, self.verbose,
            self.debug)

        self.parser = parser
        self.args = args

    def _build_args(self, attrs):
        args = {}
        for a in [a for a in attrs if getattr(self, a)]:
            args[a] = getattr(self, a)
        return args

    def add_options(self, parser):
        pass

    def execute(self, *args):
        pass


@cli_command('list', 'ls')
class List(Command):
    syntax = '[<container>[/<object>]]'
    description = 'list containers or objects'

    def add_options(self, parser):
        parser.add_option('-l', action='store_true', dest='detail',
                          default=False, help='show detailed output')
        parser.add_option('-n', action='store', type='int', dest='limit',
                          default=10000, help='show limited output')
        parser.add_option('--marker', action='store', type='str',
                          dest='marker', default=None,
                          help='show output greater then marker')
        parser.add_option('--prefix', action='store', type='str',
                          dest='prefix', default=None,
                          help='show output starting with prefix')
        parser.add_option('--delimiter', action='store', type='str',
                          dest='delimiter', default=None,
                          help='show output up to the delimiter')
        parser.add_option('--path', action='store', type='str',
                          dest='path', default=None,
                          help='show output starting with prefix up to /')
        parser.add_option('--meta', action='store', type='str',
                          dest='meta', default=None,
                          help='show output having the specified meta keys')
        parser.add_option('--if-modified-since', action='store', type='str',
                          dest='if_modified_since', default=None,
                          help='show output if modified since then')
        parser.add_option('--if-unmodified-since', action='store', type='str',
                          dest='if_unmodified_since', default=None,
                          help='show output if not modified since then')
        parser.add_option('--until', action='store', dest='until',
                          default=None, help='show metadata until that date')
        parser.add_option('--format', action='store', dest='format',
                          default='%d/%m/%Y %H:%M:%S', help='format to parse until date (default: %d/%m/%Y %H:%M:%S)')
        parser.add_option('--shared', action='store_true', dest='shared',
                          default=False, help='show only shared')
        parser.add_option('--public', action='store_true', dest='public',
                          default=False, help='show only public')

    def execute(self, container=None):
        if container:
            self.list_objects(container)
        else:
            self.list_containers()

    def list_containers(self):
        attrs = ['limit', 'marker', 'if_modified_since',
                 'if_unmodified_since', 'shared', 'public']
        args = self._build_args(attrs)
        args['format'] = 'json' if self.detail else 'text'

        if getattr(self, 'until'):
            t = _time.strptime(self.until, self.format)
            args['until'] = int(_time.mktime(t))

        l = self.client.list_containers(**args)
        print_list(l)

    def list_objects(self, container):
        #prepate params
        params = {}
        attrs = ['limit', 'marker', 'prefix', 'delimiter', 'path',
                 'meta', 'if_modified_since', 'if_unmodified_since',
                 'shared', 'public']
        args = self._build_args(attrs)
        args['format'] = 'json' if self.detail else 'text'

        if self.until:
            t = _time.strptime(self.until, self.format)
            args['until'] = int(_time.mktime(t))

        container, sep, object = container.partition('/')
        if object:
            return

        detail = 'json'
        #if request with meta quering disable trash filtering
        show_trashed = True if self.meta else False
        l = self.client.list_objects(container, **args)
        print_list(l, detail=self.detail)


@cli_command('meta')
class Meta(Command):
    syntax = '[<container>[/<object>]]'
    description = 'get account/container/object metadata'

    def add_options(self, parser):
        parser.add_option('-r', action='store_true', dest='restricted',
                          default=False, help='show only user defined metadata')
        parser.add_option('--until', action='store', dest='until',
                          default=None, help='show metadata until that date')
        parser.add_option('--format', action='store', dest='format',
                          default='%d/%m/%Y %H:%M:%S', help='format to parse until date (default: %d/%m/%Y %H:%M:%S)')
        parser.add_option('--version', action='store', dest='version',
                          default=None, help='show specific version \
                                  (applies only for objects)')

    def execute(self, path=''):
        container, sep, object = path.partition('/')
        args = {'restricted': self.restricted}
        if getattr(self, 'until'):
            t = _time.strptime(self.until, self.format)
            args['until'] = int(_time.mktime(t))

        if object:
            meta = self.client.retrieve_object_metadata(container, object,
                                                        self.restricted,
                                                        self.version)
        elif container:
            meta = self.client.retrieve_container_metadata(container, **args)
        else:
            meta = self.client.retrieve_account_metadata(**args)
        if meta is None:
            print 'Entity does not exist'
        else:
            print_dict(meta, header=None)


@cli_command('create')
class CreateContainer(Command):
    syntax = '<container> [key=val] [...]'
    description = 'create a container'

    def add_options(self, parser):
        parser.add_option('--versioning', action='store', dest='versioning',
                          default=None, help='set container versioning (auto/none)')
        parser.add_option('--quota', action='store', dest='quota',
                          default=None, help='set default container quota')

    def execute(self, container, *args):
        meta = {}
        for arg in args:
            key, sep, val = arg.partition('=')
            meta[key] = val
        policy = {}
        if getattr(self, 'versioning'):
            policy['versioning'] = self.versioning
        if getattr(self, 'quota'):
            policy['quota'] = self.quota
        ret = self.client.create_container(
            container, meta=meta, policies=policy)
        if not ret:
            print 'Container already exists'


@cli_command('delete', 'rm')
class Delete(Command):
    syntax = '<container>[/<object>]'
    description = 'delete a container or an object'

    def add_options(self, parser):
        parser.add_option('--until', action='store', dest='until',
                          default=None, help='remove history until that date')
        parser.add_option('--format', action='store', dest='format',
                          default='%d/%m/%Y %H:%M:%S', help='format to parse until date (default: %d/%m/%Y %H:%M:%S)')
        parser.add_option('--delimiter', action='store', type='str',
                          dest='delimiter', default=None,
                          help='mass delete objects with path staring with <src object> + delimiter')
        parser.add_option('-r', action='store_true',
                          dest='recursive', default=False,
                          help='mass delimiter objects with delimiter /')

    def execute(self, path):
        container, sep, object = path.partition('/')
        until = None
        if getattr(self, 'until'):
            t = _time.strptime(self.until, self.format)
            until = int(_time.mktime(t))

        kwargs = {}
        if self.delimiter:
            kwargs['delimiter'] = self.delimiter
        elif self.recursive:
            kwargs['delimiter'] = '/'

        if object:
            self.client.delete_object(container, object, until, **kwargs)
        else:
            self.client.delete_container(container, until, **kwargs)


@cli_command('get')
class GetObject(Command):
    syntax = '<container>/<object>'
    description = 'get the data of an object'

    def add_options(self, parser):
        parser.add_option('-l', action='store_true', dest='detail',
                          default=False, help='show detailed output')
        parser.add_option('--range', action='store', dest='range',
                          default=None, help='show range of data')
        parser.add_option('--if-range', action='store', dest='if_range',
                          default=None, help='show range of data')
        parser.add_option('--if-match', action='store', dest='if_match',
                          default=None, help='show output if ETags match')
        parser.add_option('--if-none-match', action='store',
                          dest='if_none_match', default=None,
                          help='show output if ETags don\'t match')
        parser.add_option('--if-modified-since', action='store', type='str',
                          dest='if_modified_since', default=None,
                          help='show output if modified since then')
        parser.add_option('--if-unmodified-since', action='store', type='str',
                          dest='if_unmodified_since', default=None,
                          help='show output if not modified since then')
        parser.add_option('-o', action='store', type='str',
                          dest='file', default=None,
                          help='save output in file')
        parser.add_option('--version', action='store', type='str',
                          dest='version', default=None,
                          help='get the specific \
                               version')
        parser.add_option('--versionlist', action='store_true',
                          dest='versionlist', default=False,
                          help='get the full object version list')
        parser.add_option('--hashmap', action='store_true',
                          dest='hashmap', default=False,
                          help='get the object hashmap instead')

    def execute(self, path):
        attrs = ['if_match', 'if_none_match', 'if_modified_since',
                 'if_unmodified_since', 'hashmap']
        args = self._build_args(attrs)
        args['format'] = 'json' if self.detail else 'text'
        if self.range:
            args['range'] = 'bytes=%s' % self.range
        if getattr(self, 'if_range'):
            args['if-range'] = 'If-Range:%s' % getattr(self, 'if_range')

        container, sep, object = path.partition('/')
        data = None
        if self.versionlist:
            if 'detail' in args.keys():
                args.pop('detail')
            args.pop('format')
            self.detail = True
            data = self.client.retrieve_object_versionlist(
                container, object, **args)
        elif self.version:
            data = self.client.retrieve_object_version(container, object,
                                                       self.version, **args)
        elif self.hashmap:
            if 'detail' in args.keys():
                args.pop('detail')
            args.pop('format')
            self.detail = True
            data = self.client.retrieve_object_hashmap(
                container, object, **args)
        else:
            data = self.client.retrieve_object(container, object, **args)

        f = open(self.file, 'w') if self.file else stdout
        if self.detail or isinstance(data, types.DictionaryType):
            if self.versionlist:
                print_versions(data, f=f)
            else:
                print_dict(data, f=f)
        else:
            f.write(data)
        f.close()


@cli_command('mkdir')
class PutMarker(Command):
    syntax = '<container>/<directory marker>'
    description = 'create a directory marker'

    def execute(self, path):
        container, sep, object = path.partition('/')
        self.client.create_directory_marker(container, object)


@cli_command('put')
class PutObject(Command):
    syntax = '<container>/<object> [key=val] [...]'
    description = 'create/override object'

    def add_options(self, parser):
        parser.add_option(
            '--use_hashes', action='store_true', dest='use_hashes',
            default=False, help='provide hashmap instead of data')
        parser.add_option('--chunked', action='store_true', dest='chunked',
                          default=False, help='set chunked transfer mode')
        parser.add_option('--etag', action='store', dest='etag',
                          default=None, help='check written data')
        parser.add_option('--content-encoding', action='store',
                          dest='content_encoding', default=None,
                          help='provide the object MIME content type')
        parser.add_option('--content-disposition', action='store', type='str',
                          dest='content_disposition', default=None,
                          help='provide the presentation style of the object')
        #parser.add_option('-S', action='store',
        #                  dest='segment_size', default=False,
        #                  help='use for large file support')
        parser.add_option('--manifest', action='store',
                          dest='x_object_manifest', default=None,
                          help='provide object parts prefix in <container>/<object> form')
        parser.add_option('--content-type', action='store',
                          dest='content_type', default=None,
                          help='create object with specific content type')
        parser.add_option('--sharing', action='store',
                          dest='x_object_sharing', default=None,
                          help='define sharing object policy')
        parser.add_option('-f', action='store',
                          dest='srcpath', default=None,
                          help='file descriptor to read from (pass - for standard input)')
        parser.add_option('--public', action='store_true',
                          dest='x_object_public', default=False,
                          help='make object publicly accessible')

    def execute(self, path, *args):
        if path.find('=') != -1:
            raise Fault('Missing path argument')

        #prepare user defined meta
        meta = {}
        for arg in args:
            key, sep, val = arg.partition('=')
            meta[key] = val

        attrs = ['etag', 'content_encoding', 'content_disposition',
                 'content_type', 'x_object_sharing', 'x_object_public']
        args = self._build_args(attrs)

        container, sep, object = path.partition('/')

        f = None
        if self.srcpath:
            f = open(self.srcpath) if self.srcpath != '-' else stdin

        if self.use_hashes and not f:
            raise Fault('Illegal option combination')

        if self.chunked:
            self.client.create_object_using_chunks(container, object, f,
                                                   meta=meta, **args)
        elif self.use_hashes:
            data = f.read()
            hashmap = json.loads(data)
            self.client.create_object_by_hashmap(container, object, hashmap,
                                                 meta=meta, **args)
        elif self.x_object_manifest:
            self.client.create_manifestation(
                container, object, self.x_object_manifest)
        elif not f:
            self.client.create_zero_length_object(
                container, object, meta=meta, **args)
        else:
            self.client.create_object(container, object, f, meta=meta, **args)
        if f:
            f.close()


@cli_command('copy', 'cp')
class CopyObject(Command):
    syntax = '<src container>/<src object> [<dst container>/]<dst object> [key=val] [...]'
    description = 'copy an object to a different location'

    def add_options(self, parser):
        parser.add_option('--version', action='store',
                          dest='version', default=False,
                          help='copy specific version')
        parser.add_option('--public', action='store_true',
                          dest='public', default=False,
                          help='make object publicly accessible')
        parser.add_option('--content-type', action='store',
                          dest='content_type', default=None,
                          help='change object\'s content type')
        parser.add_option('--delimiter', action='store', type='str',
                          dest='delimiter', default=None,
                          help='mass copy objects with path staring with <src object> + delimiter')
        parser.add_option('-r', action='store_true',
                          dest='recursive', default=False,
                          help='mass copy with delimiter /')

    def execute(self, src, dst, *args):
        src_container, sep, src_object = src.partition('/')
        dst_container, sep, dst_object = dst.partition('/')

        #prepare user defined meta
        meta = {}
        for arg in args:
            key, sep, val = arg.partition('=')
            meta[key] = val

        if not sep:
            dst_container = src_container
            dst_object = dst

        args = {'content_type': self.content_type} if self.content_type else {}
        if self.delimiter:
            args['delimiter'] = self.delimiter
        elif self.recursive:
            args['delimiter'] = '/'
        self.client.copy_object(src_container, src_object, dst_container,
                                dst_object, meta, self.public, self.version,
                                **args)


@cli_command('set')
class SetMeta(Command):
    syntax = '[<container>[/<object>]] key=val [key=val] [...]'
    description = 'set account/container/object metadata'

    def execute(self, path, *args):
        #in case of account fix the args
        if path.find('=') != -1:
            args = list(args)
            args.append(path)
            args = tuple(args)
            path = ''
        meta = {}
        for arg in args:
            key, sep, val = arg.partition('=')
            meta[key.strip()] = val.strip()
        container, sep, object = path.partition('/')
        if object:
            self.client.update_object_metadata(container, object, **meta)
        elif container:
            self.client.update_container_metadata(container, **meta)
        else:
            self.client.update_account_metadata(**meta)


@cli_command('update')
class UpdateObject(Command):
    syntax = '<container>/<object> path [key=val] [...]'
    description = 'update object metadata/data (default mode: append)'

    def add_options(self, parser):
        parser.add_option('-a', action='store_true', dest='append',
                          default=True, help='append data')
        parser.add_option('--offset', action='store',
                          dest='offset',
                          default=None, help='starting offest to be updated')
        parser.add_option('--range', action='store', dest='content_range',
                          default=None, help='range of data to be updated')
        parser.add_option('--chunked', action='store_true', dest='chunked',
                          default=False, help='set chunked transfer mode')
        parser.add_option('--content-encoding', action='store',
                          dest='content_encoding', default=None,
                          help='provide the object MIME content type')
        parser.add_option('--content-disposition', action='store', type='str',
                          dest='content_disposition', default=None,
                          help='provide the presentation style of the object')
        parser.add_option('--manifest', action='store', type='str',
                          dest='x_object_manifest', default=None,
                          help='use for large file support')
        parser.add_option('--sharing', action='store',
                          dest='x_object_sharing', default=None,
                          help='define sharing object policy')
        parser.add_option('--nosharing', action='store_true',
                          dest='no_sharing', default=None,
                          help='clear object sharing policy')
        parser.add_option('-f', action='store',
                          dest='srcpath', default=None,
                          help='file descriptor to read from: pass - for standard input')
        parser.add_option('--public', action='store_true',
                          dest='x_object_public', default=False,
                          help='make object publicly accessible')
        parser.add_option('--replace', action='store_true',
                          dest='replace', default=False,
                          help='override metadata')

    def execute(self, path, *args):
        if path.find('=') != -1:
            raise Fault('Missing path argument')

        #prepare user defined meta
        meta = {}
        for arg in args:
            key, sep, val = arg.partition('=')
            meta[key] = val

        attrs = ['content_encoding', 'content_disposition', 'x_object_sharing',
                 'x_object_public', 'x_object_manifest', 'replace', 'offset',
                 'content_range']
        args = self._build_args(attrs)

        if self.no_sharing:
            args['x_object_sharing'] = ''

        container, sep, object = path.partition('/')

        f = None
        if self.srcpath:
            f = open(self.srcpath) if self.srcpath != '-' else stdin

        if self.chunked:
            self.client.update_object_using_chunks(container, object, f,
                                                   meta=meta, **args)
        else:
            self.client.update_object(container, object, f, meta=meta, **args)
        if f:
            f.close()


@cli_command('move', 'mv')
class MoveObject(Command):
    syntax = '<src container>/<src object> [<dst container>/]<dst object>'
    description = 'move an object to a different location'

    def add_options(self, parser):
        parser.add_option('--public', action='store_true',
                          dest='public', default=False,
                          help='make object publicly accessible')
        parser.add_option('--content-type', action='store',
                          dest='content_type', default=None,
                          help='change object\'s content type')
        parser.add_option('--delimiter', action='store', type='str',
                          dest='delimiter', default=None,
                          help='mass move objects with path staring with <src object> + delimiter')
        parser.add_option('-r', action='store_true',
                          dest='recursive', default=False,
                          help='mass move objects with delimiter /')

    def execute(self, src, dst, *args):
        src_container, sep, src_object = src.partition('/')
        dst_container, sep, dst_object = dst.partition('/')
        if not sep:
            dst_container = src_container
            dst_object = dst

        #prepare user defined meta
        meta = {}
        for arg in args:
            key, sep, val = arg.partition('=')
            meta[key] = val

        args = {'content_type': self.content_type} if self.content_type else {}
        if self.delimiter:
            args['delimiter'] = self.delimiter
        elif self.recursive:
            args['delimiter'] = '/'
        self.client.move_object(src_container, src_object, dst_container,
                                dst_object, meta, self.public, **args)


@cli_command('unset')
class UnsetObject(Command):
    syntax = '<container>/[<object>] key [key] [...]'
    description = 'delete metadata info'

    def execute(self, path, *args):
        #in case of account fix the args
        if len(args) == 0:
            args = list(args)
            args.append(path)
            args = tuple(args)
            path = ''
        meta = []
        for key in args:
            meta.append(key)
        container, sep, object = path.partition('/')
        if object:
            self.client.delete_object_metadata(container, object, meta)
        elif container:
            self.client.delete_container_metadata(container, meta)
        else:
            self.client.delete_account_metadata(meta)


@cli_command('group')
class CreateGroup(Command):
    syntax = 'key=val [key=val] [...]'
    description = 'create account groups'

    def execute(self, *args):
        groups = {}
        for arg in args:
            key, sep, val = arg.partition('=')
            groups[key] = val
        self.client.set_account_groups(**groups)


@cli_command('ungroup')
class DeleteGroup(Command):
    syntax = 'key [key] [...]'
    description = 'delete account groups'

    def execute(self, *args):
        groups = []
        for arg in args:
            groups.append(arg)
        self.client.unset_account_groups(groups)


@cli_command('policy')
class SetPolicy(Command):
    syntax = 'container key=val [key=val] [...]'
    description = 'set container policies'

    def execute(self, path, *args):
        if path.find('=') != -1:
            raise Fault('Missing container argument')

        container, sep, object = path.partition('/')

        if object:
            raise Fault('Only containers have policies')

        policies = {}
        for arg in args:
            key, sep, val = arg.partition('=')
            policies[key] = val

        self.client.set_container_policies(container, **policies)


@cli_command('publish')
class PublishObject(Command):
    syntax = '<container>/<object>'
    description = 'publish an object'

    def execute(self, src):
        src_container, sep, src_object = src.partition('/')

        self.client.publish_object(src_container, src_object)


@cli_command('unpublish')
class UnpublishObject(Command):
    syntax = '<container>/<object>'
    description = 'unpublish an object'

    def execute(self, src):
        src_container, sep, src_object = src.partition('/')

        self.client.unpublish_object(src_container, src_object)


@cli_command('sharing')
class SharingObject(Command):
    syntax = 'list users sharing objects with the user'
    description = 'list user accounts sharing objects with the user'

    def add_options(self, parser):
        parser.add_option('-l', action='store_true', dest='detail',
                          default=False, help='show detailed output')
        parser.add_option('-n', action='store', type='int', dest='limit',
                          default=10000, help='show limited output')
        parser.add_option('--marker', action='store', type='str',
                          dest='marker', default=None,
                          help='show output greater then marker')

    def execute(self):
        attrs = ['limit', 'marker']
        args = self._build_args(attrs)
        args['format'] = 'json' if self.detail else 'text'

        print_list(self.client.list_shared_by_others(**args))


@cli_command('send')
class Send(Command):
    syntax = '<file> <container>[/<prefix>]'
    description = 'upload file to container (using prefix)'

    def execute(self, file, path):
        container, sep, prefix = path.partition('/')
        upload(self.client, file, container, prefix)


@cli_command('receive')
class Receive(Command):
    syntax = '<container>/<object> <file>'
    description = 'download object to file'

    def execute(self, path, file):
        container, sep, object = path.partition('/')
        download(self.client, container, object, file)


def print_usage():
    cmd = Command('', [])
    parser = cmd.parser
    parser.usage = '%prog <command> [options]'
    parser.print_help()

    commands = []
    for cls in set(_cli_commands.values()):
        name = ', '.join(cls.commands)
        description = getattr(cls, 'description', '')
        commands.append('  %s %s' % (name.ljust(12), description))
    print '\nCommands:\n' + '\n'.join(sorted(commands))


def print_dict(d, header='name', f=stdout, detail=True):
    header = header if header in d else 'subdir'
    if header and header in d:
        f.write('%s\n' % d.pop(header).encode('utf8'))
    if detail:
        patterns = ['^x_(account|container|object)_meta_(\w+)$']
        patterns.append(patterns[0].replace('_', '-'))
        for key, val in sorted(d.items()):
            f.write('%s: %s\n' % (key.rjust(30), val))


def print_list(l, verbose=False, f=stdout, detail=True):
    for elem in l:
        #if it's empty string continue
        if not elem:
            continue
        if isinstance(elem, types.DictionaryType):
            print_dict(elem, f=f, detail=detail)
        elif isinstance(elem, types.StringType):
            if not verbose:
                elem = elem.split('Traceback')[0]
            f.write('%s\n' % elem)
        else:
            f.write('%s\n' % elem)


def print_versions(data, f=stdout):
    if 'versions' not in data:
        f.write('%s\n' % data)
        return
    f.write('versions:\n')
    for id, t in data['versions']:
        f.write('%s @ %s\n' % (str(id).rjust(30),
                datetime.fromtimestamp(float(t))))


def main():
    try:
        name = argv[1]
        cls = class_for_cli_command(name)
    except (IndexError, KeyError):
        print_usage()
        exit(1)

    cmd = cls(name, argv[2:])

    try:
        cmd.execute(*cmd.args)
    except TypeError, e:
        cmd.parser.print_help()
        exit(1)
    except Fault, f:
        status = '%s ' % f.status if f.status else ''
        print '%s%s' % (status, f.data)


if __name__ == '__main__':
    main()
