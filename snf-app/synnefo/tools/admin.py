#!/usr/bin/env python

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

from django.core.management import setup_environ
try:
    from synnefo import settings
except ImportError:
    raise Exception("Cannot import settings, make sure PYTHONPATH contains "
                    "the parent directory of the Synnefo Django project.")
setup_environ(settings)

import inspect
import sys

from collections import defaultdict
from itertools import product
from optparse import OptionParser
from os.path import basename

from synnefo.db import models
from synnefo.logic import backend, users
from synnefo.plankton.backend import ImageBackend
from synnefo.util.dictconfig import dictConfig


def print_dict(d, exclude=()):
    if not d:
        return
    margin = max(len(key) for key in d) + 1

    for key, val in sorted(d.items()):
        if key in exclude or key.startswith('_'):
            continue
        print '%s: %s' % (key.rjust(margin), val)

def print_item(item):
    name = getattr(item, 'name', '')
    print '%d %s' % (item.id, name)
    print_dict(item.__dict__, exclude=('id', 'name'))

def print_items(items, detail=False, keys=None):
    keys = keys or ('id', 'name')
    for item in items:
        for key in keys:
            print getattr(item, key),
        print
        
        if detail:
            print_dict(item.__dict__, exclude=keys)
            print


class Command(object):
    group = '<group>'
    name = '<command>'
    syntax = ''
    description = ''
    hidden = False
    
    def __init__(self, exe, argv):
        parser = OptionParser()
        syntax = '%s [options]' % self.syntax if self.syntax else '[options]'
        parser.usage = '%s %s %s' % (exe, self.name, syntax)
        parser.description = self.description
        self.add_options(parser)
        options, self.args = parser.parse_args(argv)
        
        # Add options to self
        for opt in parser.option_list:
            key = opt.dest
            if key:
                val = getattr(options, key)
                setattr(self, key, val)
        
        self.parser = parser
    
    def add_options(self, parser):
        pass
    
    def execute(self):
        try:
            self.main(*self.args)
        except TypeError:
            self.parser.print_help()


# Server commands

class ListServers(Command):
    group = 'server'
    name = 'list'
    syntax = '[server id]'
    description = 'list servers'
    
    def add_options(self, parser):
        parser.add_option('-a', action='store_true', dest='show_deleted',
                        default=False, help='also list deleted servers')
        parser.add_option('-l', action='store_true', dest='detail',
                        default=False, help='show detailed output')
        parser.add_option('-u', dest='uid', metavar='UID',
                            help='show servers of user with id UID')
    
    def main(self, server_id=None):
        if server_id:
            servers = [models.VirtualMachine.objects.get(id=server_id)]
        else:
            servers = models.VirtualMachine.objects.order_by('id')
            if not self.show_deleted:
                servers = servers.exclude(deleted=True)
            if self.uid:
                servers = servers.filter(userid=self.uid)
        
        print_items(servers, self.detail)


# Image commands

class ListImages(Command):
    group = 'image'
    name = 'list'
    syntax = '[image id]'
    description = 'list images'
    
    def add_options(self, parser):
        parser.add_option('-a', action='store_true', dest='show_deleted',
                default=False, help='also list deleted images')
        parser.add_option('-l', action='store_true', dest='detail',
                default=False, help='show detailed output')
        parser.add_option('-p', action='store_true', dest='pithos',
                default=False, help='show images stored in Pithos')
        parser.add_option('--user', dest='user',
                default=settings.SYSTEM_IMAGES_OWNER,
                metavar='USER',
                help='list images accessible to USER')
    
    def main(self, image_id=None):
        if self.pithos:
            return self.main_pithos(image_id)
        
        if image_id:
            images = [models.Image.objects.get(id=image_id)]
        else:
            images = models.Image.objects.order_by('id')
            if not self.show_deleted:
                images = images.exclude(state='DELETED')
        print_items(images, self.detail)
    
    def main_pithos(self, image_id=None):
        backend = ImageBackend(self.user)
        if image_id:
            images = [backend.get_image(image_id)]
        else:
            images = backend.iter_shared()
        
        for image in images:
            print image['id'], image['name']
            if self.detail:
                print_dict(image, exclude=('id',))
                print
        
        backend.close()


class RegisterImage(Command):
    group = 'image'
    name = 'register'
    syntax = '<name> <Backend ID or Pithos URL> <disk format>'
    description = 'register an image'
    
    def add_options(self, parser):
        parser.add_option('--meta', dest='meta', action='append',
                metavar='KEY=VAL',
                help='add metadata (can be used multiple times)')
        parser.add_option('--public', action='store_true', dest='public',
                default=False, help='make image public')
        parser.add_option('-u', dest='uid', metavar='UID',
                help='assign image to user with id UID')
    
    def main(self, name, backend_id, format):
        if backend_id.startswith('pithos://'):
            return self.main_pithos(name, backend_id, format)
        
        formats = [x[0] for x in models.Image.FORMATS]
        if format not in formats:
            valid = ', '.join(formats)
            print 'Invalid format. Must be one of:', valid
            return
        
        image = models.Image.objects.create(
            name=name,
            state='ACTIVE',
            owner=self.uid,
            backend_id=backend_id,
            format=format,
            public=self.public)
        
        if self.meta:
            for m in self.meta:
                key, sep, val = m.partition('=')
                if key and val:
                    image.metadata.create(meta_key=key, meta_value=val)
                else:
                    print 'WARNING: Ignoring meta', m
        
        print_item(image)
    
    def main_pithos(self, name, url, disk_format):
        if disk_format not in settings.ALLOWED_DISK_FORMATS:
            print 'Invalid disk format'
            return
        
        params = {
            'disk_format': disk_format,
            'is_public': self.public,
            'properties': {}}
        
        if self.meta:
            for m in self.meta:
                key, sep, val = m.partition('=')
                if key and val:
                    params['properties'][key] = val
                else:
                    print 'WARNING: Ignoring meta', m
        
        backend = ImageBackend(self.uid or settings.SYSTEM_IMAGES_OWNER)
        backend.register(name, url, params)
        backend.close()


class UploadImage(Command):
    group = 'image'
    name = 'upload'
    syntax = '<name> <path>'
    description = 'upload an image'
    
    def add_options(self, parser):
        container_formats = ', '.join(settings.ALLOWED_CONTAINER_FORMATS)
        disk_formats = ', '.join(settings.ALLOWED_DISK_FORMATS)
        
        parser.add_option('--container-format', dest='container_format',
                default=settings.DEFAULT_CONTAINER_FORMAT,
                metavar='FORMAT',
                help='set container format (%s)' % container_formats)
        parser.add_option('--disk-format', dest='disk_format',
                default=settings.DEFAULT_DISK_FORMAT,
                metavar='FORMAT',
                help='set disk format (%s)' % disk_formats)
        parser.add_option('--meta', dest='meta', action='append',
                metavar='KEY=VAL',
                help='add metadata (can be used multiple times)')
        parser.add_option('--owner', dest='owner',
                default=settings.SYSTEM_IMAGES_OWNER,
                metavar='USER',
                help='set owner to USER')
        parser.add_option('--public', action='store_true', dest='public',
                default=False,
                help='make image public')
    
    def main(self, name, path):
        backend = ImageBackend(self.owner)
        
        params = {
            'container_format': self.container_format,
            'disk_format': self.disk_format,
            'is_public': self.public,
            'filename': basename(path),
            'properties': {}}
        
        if self.meta:
            for m in self.meta:
                key, sep, val = m.partition('=')
                if key and val:
                    params['properties'][key] = val
                else:
                    print 'WARNING: Ignoring meta', m
        
        with open(path) as f:
            backend.put(name, f, params)
        
        backend.close()


class UpdateImage(Command):
    group = 'image'
    name = 'update'
    syntax = '<image id>'
    description = 'update an image stored in Pithos'
    
    def add_options(self, parser):
        container_formats = ', '.join(settings.ALLOWED_CONTAINER_FORMATS)
        disk_formats = ', '.join(settings.ALLOWED_DISK_FORMATS)
        
        parser.add_option('--container-format', dest='container_format',
                metavar='FORMAT',
                help='set container format (%s)' % container_formats)
        parser.add_option('--disk-format', dest='disk_format',
                metavar='FORMAT',
                help='set disk format (%s)' % disk_formats)
        parser.add_option('--name', dest='name',
                metavar='NAME',
                help='set name to NAME')
        parser.add_option('--private', action='store_true', dest='private',
                help='make image private')
        parser.add_option('--public', action='store_true', dest='public',
                help='make image public')
        parser.add_option('--user', dest='user',
                default=settings.SYSTEM_IMAGES_OWNER,
                metavar='USER',
                help='connect as USER')
    
    def main(self, image_id):
        backend = ImageBackend(self.user)
        
        image = backend.get_image(image_id)
        if not image:
            print 'Image not found'
            return
        
        params = {}
        
        if self.container_format:
            if self.container_format not in settings.ALLOWED_CONTAINER_FORMATS:
                print 'Invalid container format'
                return
            params['container_format'] = self.container_format
        if self.disk_format:
            if self.disk_format not in settings.ALLOWED_DISK_FORMATS:
                print 'Invalid disk format'
                return
            params['disk_format'] = self.disk_format
        if self.name:
            params['name'] = self.name
        if self.private:
            params['is_public'] = False
        if self.public:
            params['is_public'] = True
        
        backend.update(image_id, params)
        backend.close()


class ModifyImage(Command):
    group = 'image'
    name = 'modify'
    syntax = '<image id>'
    description = 'modify an image'
    
    def add_options(self, parser):
        states = ', '.join(x[0] for x in models.Image.IMAGE_STATES)
        formats = ', '.join(x[0] for x in models.Image.FORMATS)

        parser.add_option('-b', dest='backend_id', metavar='BACKEND_ID',
                help='set image backend id')
        parser.add_option('-f', dest='format', metavar='FORMAT',
                help='set image format (%s)' % formats)
        parser.add_option('-n', dest='name', metavar='NAME',
                help='set image name')
        parser.add_option('--public', action='store_true', dest='public',
                help='make image public')
        parser.add_option('--nopublic', action='store_true', dest='private',
                help='make image private')
        parser.add_option('-s', dest='state', metavar='STATE',
                help='set image state (%s)' % states)
        parser.add_option('-u', dest='uid', metavar='UID',
                help='assign image to user with id UID')
    
    def main(self, image_id):
        try:
            image = models.Image.objects.get(id=image_id)
        except:
            print 'Image not found'
            return
        
        if self.backend_id:
            image.backend_id = self.backend_id
        if self.format:
            allowed = [x[0] for x in models.Image.FORMATS]
            if self.format not in allowed:
                valid = ', '.join(allowed)
                print 'Invalid format. Must be one of:', valid
                return
            image.format = self.format
        if self.name:
            image.name = self.name
        if self.public:
            image.public = True
        if self.private:
            image.public = False
        if self.state:
            allowed = [x[0] for x in models.Image.IMAGE_STATES]
            if self.state not in allowed:
                valid = ', '.join(allowed)
                print 'Invalid state. Must be one of:', valid
                return
            image.state = self.state
        
        image.userid = self.uid
        
        image.save()
        print_item(image)


class ModifyImageMeta(Command):
    group = 'image'
    name = 'meta'
    syntax = '<image id> [key[=val]]'
    description = 'get and manipulate image metadata'
    
    def add_options(self, parser):
        parser.add_option('--user', dest='user',
                default=settings.SYSTEM_IMAGES_OWNER,
                metavar='USER',
                help='connect as USER')

    def main(self, image_id, arg=''):
        if not image_id.isdigit():
            return self.main_pithos(image_id, arg)
        
        try:
            image = models.Image.objects.get(id=image_id)
        except:
            print 'Image not found'
            return
        
        key, sep, val = arg.partition('=')
        if not sep:
            val = None
        
        if not key:
            metadata = {}
            for meta in image.metadata.order_by('meta_key'):
                metadata[meta.meta_key] = meta.meta_value
            print_dict(metadata)
            return
        
        try:
            meta = image.metadata.get(meta_key=key)
        except models.ImageMetadata.DoesNotExist:
            meta = None
        
        if val is None:
            if meta:
                print_dict({key: meta.meta_value})
            return
        
        if val:
            if not meta:
                meta = image.metadata.create(meta_key=key)
            meta.meta_value = val
            meta.save()
        else:
            # Delete if val is empty
            if meta:
                meta.delete()
    
    def main_pithos(self, image_id, arg=''):
        backend = ImageBackend(self.user)
                
        try:
            image = backend.get_image(image_id)
            if not image:
                print 'Image not found'
                return
            
            key, sep, val = arg.partition('=')
            if not sep:
                val = None
            
            properties = image.get('properties', {})
            
            if not key:
                print_dict(properties)
                return
            
            if val is None:
                if key in properties:
                    print_dict({key: properties[key]})
                return
            
            if val:
                properties[key] = val        
                params = {'properties': properties}
                backend.update(image_id, params)
        finally:
            backend.close()


# Flavor commands

class CreateFlavor(Command):
    group = 'flavor'
    name = 'create'
    syntax = '<cpu>[,<cpu>,...] <ram>[,<ram>,...] <disk>[,<disk>,...]'
    description = 'create one or more flavors'
    
    def add_options(self, parser):
        disk_templates = ', '.join(t for t in settings.GANETI_DISK_TEMPLATES)
        parser.add_option('--disk-template',
            dest='disk_template',
            metavar='TEMPLATE',
            default=settings.DEFAULT_GANETI_DISK_TEMPLATE,
            help='available disk templates: %s' % disk_templates)
    
    def main(self, cpu, ram, disk):
        cpus = cpu.split(',')
        rams = ram.split(',')
        disks = disk.split(',')
        
        flavors = []
        for cpu, ram, disk in product(cpus, rams, disks):
            try:
                flavors.append((int(cpu), int(ram), int(disk)))
            except ValueError:
                print 'Invalid values'
                return
        
        created = []
        
        for cpu, ram, disk in flavors:
            flavor = models.Flavor.objects.create(
                cpu=cpu,
                ram=ram,
                disk=disk,
                disk_template=self.disk_template)
            created.append(flavor)
        
        print_items(created, detail=True)


class DeleteFlavor(Command):
    group = 'flavor'
    name = 'delete'
    syntax = '<flavor id> [<flavor id>] [...]'
    description = 'delete one or more flavors'
    
    def main(self, *args):
        if not args:
            raise TypeError
        for flavor_id in args:
            flavor = models.Flavor.objects.get(id=int(flavor_id))
            flavor.deleted = True
            flavor.save()


class ListFlavors(Command):
    group = 'flavor'
    name = 'list'
    syntax = '[flavor id]'
    description = 'list images'
    
    def add_options(self, parser):
        parser.add_option('-a', action='store_true', dest='show_deleted',
                default=False, help='also list deleted flavors')
        parser.add_option('-l', action='store_true', dest='detail',
                        default=False, help='show detailed output')
    
    def main(self, flavor_id=None):
        if flavor_id:
            flavors = [models.Flavor.objects.get(id=flavor_id)]
        else:
            flavors = models.Flavor.objects.order_by('id')
            if not self.show_deleted:
                flavors = flavors.exclude(deleted=True)
        print_items(flavors, self.detail)


class ShowStats(Command):
    group = 'stats'
    name = None
    description = 'show statistics'

    def main(self):
        stats = {}
        stats['Images'] = models.Image.objects.exclude(state='DELETED').count()
        stats['Flavors'] = models.Flavor.objects.count()
        stats['VMs'] = models.VirtualMachine.objects.filter(deleted=False).count()
        stats['Networks'] = models.Network.objects.exclude(state='DELETED').count()
        
        stats['Ganeti Instances'] = len(backend.get_ganeti_instances())
        stats['Ganeti Nodes'] = len(backend.get_ganeti_nodes())
        stats['Ganeti Jobs'] = len(backend.get_ganeti_jobs())
        
        print_dict(stats)


def print_usage(exe, groups, group=None, shortcut=False):
    nop = Command(exe, [])
    nop.parser.print_help()
    if group:
        groups = {group: groups[group]}

    print
    print 'Commands:'
    
    for group, commands in sorted(groups.items()):
        for command, cls in sorted(commands.items()):
            if cls.hidden:
                continue
            name = '  %s %s' % (group, command or '')
            print '%s %s' % (name.ljust(22), cls.description)
        print


def main():
    groups = defaultdict(dict)
    module = sys.modules[__name__]
    for name, cls in inspect.getmembers(module, inspect.isclass):
        if not issubclass(cls, Command) or cls == Command:
            continue
        groups[cls.group][cls.name] = cls
    
    argv = list(sys.argv)
    exe = basename(argv.pop(0))
    prefix, sep, suffix = exe.partition('-')
    if sep and prefix == 'snf' and suffix in groups:
        # Allow shortcut aliases like snf-image, snf-server, etc
        group = suffix
    else:
        group = argv.pop(0) if argv else None
        if group in groups:
            exe = '%s %s' % (exe, group)
        else:
            exe = '%s <group>' % exe
            group = None
    
    command = argv.pop(0) if argv else None
    
    if group not in groups or command not in groups[group]:
        print_usage(exe, groups, group)
        sys.exit(1)
    
    cls = groups[group][command]
    cmd = cls(exe, argv)
    cmd.execute()


if __name__ == '__main__':
    dictConfig(settings.SNFADMIN_LOGGING)
    main()
