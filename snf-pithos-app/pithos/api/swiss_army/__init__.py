# Copyright 2012 GRNET S.A. All rights reserved.
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

from pithos.api.util import get_backend, split_container_object_string

import re
import hashlib
import os


def data_read_iterator(str, size=1024):
    offset = 0
    while True:
        data = str[offset:offset + size]
        offset = offset + size
        if not data:
            break
        yield data


class SwissArmy():
    def __init__(self):
        self.backend = get_backend()

    def cleanup(self):
        self.backend.close()

    def existing_accounts(self):
        return sorted([path for path, _ in self.backend.node.node_accounts()])

    def duplicate_accounts(self):
        accounts = self.existing_accounts()
        duplicates = []
        for i in range(len(accounts)):
            account = accounts[i]
            matcher = re.compile(account, re.IGNORECASE)
            duplicate = filter(matcher.match, (i for i in accounts[i + 1:] \
                if len(i) == len(account)))
            if duplicate:
                duplicate.insert(0, account)
                duplicates.append(duplicate)
        return duplicates

    def list_all_containers(self, account, step=10):
        containers = []
        marker = None
        while 1:
            more = self.backend.list_containers(account, account, limit=10,
                                                marker=marker)
            if not more:
                break
            containers.extend(more)
            marker = more[-1]
        return containers

    def list_all_container_objects(self, account, container, virtual=False):
        objects = []
        marker = None
        while 1:
            more = self.backend.list_objects(account, account, container,
                                             marker=marker, virtual=virtual)
            if not more:
                break
            objects.extend((i[0] for i in more))
            marker = more[-1][0]
        return objects

    def list_all_objects(self, account, virtual=False):
        containers = self.list_all_containers(account)
        objects = []
        extend = objects.extend
        for c in containers:
            more = self.list_all_container_objects(account, c, virtual=virtual)
            extend([os.path.join(c, i) for i in more])
        return objects

    def list_past_versions(self, account, container, name):
        versions = self.backend.list_versions(account, account, container,
                                              name)
        # do not return the current version
        return list(x[0] for x in versions[:-1])

    def move_object(self, src_account, src_container, src_name,
                    dest_account, dry=True, silent=False):
        if src_account not in self.existing_accounts():
            raise NameError('%s does not exist' % src_account)
        if dest_account not in self.existing_accounts():
            raise NameError('%s does not exist' % dest_account)

        trans = self.backend.wrapper.conn.begin()
        try:
            self._copy_object(src_account, src_container, src_name,
                              dest_account, move=True)

            if dry:
                if not silent:
                    print "Skipping database commit."
                trans.rollback()
            else:
                trans.commit()
                if not silent:
                    print "%s is deleted." % src_account
        except:
            trans.rollback()
            raise

    def _copy_object(self, src_account, src_container, src_name,
                    dest_account, move=False):
        path = os.path.join(src_container, src_name)
        fullpath = os.path.join(src_account, path)
        dest_container = src_container
        dest_name = src_name

        meta = self.backend.get_object_meta(src_account, src_account,
                                            src_container, src_name, 'pithos',
                                            version=None)
        content_type = meta.get('type')

        # get source object history
        versions = self.list_past_versions(src_account, src_container,
                                           src_name)

        # get source object permissions
        permissions = self.backend.permissions.access_get(fullpath)

        # get source object public
        public = self.backend.get_object_public(src_account, src_account,
                                                src_container, src_name)

        if dest_container in self.backend.list_containers(dest_account,
                                                          dest_account):
            # Note: if dest_container contains an object with the same name
            # a new version with the contents of the source object will be
            # created and the one in the destination container will pass to
            # history
            self.backend.copy_object(dest_account, src_account, src_container,
                                     src_name, dest_account, dest_container,
                                     dest_name, content_type, 'pithos',
                                     meta={}, replace_meta=False,
                                     permissions=permissions)
        else:
            # create destination container and retry
            self.backend.put_container(dest_account, dest_account,
                                       dest_container)
            self.backend.copy_object(dest_account, src_account, src_container,
                                     src_name, dest_account, dest_container,
                                     dest_name, content_type, 'pithos',
                                     meta={}, replace_meta=False,
                                     permissions=permissions)

        if move:
            self.backend.delete_object(src_account, src_account,
                                       src_container, src_name)

        dest_path, dest_node = self.backend._lookup_object(dest_account,
                                                           dest_container,
                                                           dest_name)
        assert dest_path == '/'.join([dest_account, path])

        # turn history versions to point to the newly created node
        for serial in versions:
            self.backend.node.version_put_property(serial, 'node', dest_node)

        if public:
            # set destination object public
            fullpath = '/'.join([dest_account, dest_container, dest_name])
            self.backend.permissions.public_set(
                fullpath,
                self.backend.public_url_security,
                self.backend.public_url_alphabet
            )

    def _merge_account(self, src_account, dest_account, delete_src=False):
            # TODO: handle exceptions
            # copy all source objects
            for path in self.list_all_objects(src_account):
                src_container, src_name = split_container_object_string(
                    '/%s' % path)

                # give read permissions to the dest_account
                permissions = self.backend.get_object_permissions(
                    src_account, src_account, src_container, src_name)
                if permissions:
                    permissions = permissions[2]
                permissions['read'] = permissions.get('read', [])
                permissions['read'].append(dest_account)
                self.backend.update_object_permissions(src_account,
                                                       src_account,
                                                       src_container,
                                                       src_name,
                                                       permissions)

                self._copy_object(src_account, src_container, src_name,
                                 dest_account, move=delete_src)

            # move groups also
            groups = self.backend.get_account_groups(src_account, src_account)
            (v.replace(src_account, dest_account) for v in groups.values())
            self.backend.update_account_groups(dest_account, dest_account,
                                               groups)
            if delete_src:
                self._delete_account(src_account)

    def merge_account(self, src_account, dest_account, only_stats=True,
                      dry=True, silent=False, delete_src=False):
        if src_account not in self.existing_accounts():
            raise NameError('%s does not exist' % src_account)
        if dest_account not in self.existing_accounts():
            raise NameError('%s does not exist' % dest_account)

        if only_stats:
            print "The following %s's entries will be moved to %s:" \
                % (src_account, dest_account)
            print "Objects: %r" % self.list_all_objects(src_account)
            print "Groups: %r" \
                % self.backend.get_account_groups(src_account,
                                                  src_account).keys()
            return

        trans = self.backend.wrapper.conn.begin()
        try:
            self._merge_account(src_account, dest_account, delete_src)

            if dry:
                if not silent:
                    print "Skipping database commit."
                trans.rollback()
            else:
                trans.commit()
                if not silent:
                    msg = "%s merged into %s."
                    print msg % (src_account, dest_account)
        except:
            trans.rollback()
            raise

    def delete_container_contents(self, account, container):
        self.backend.delete_container(account, account, container,
                                      delimiter='/')

    def delete_container(self, account, container):
        self.backend.delete_container(account, account, container)

    def _delete_account(self, account):
        for c in self.list_all_containers(account):
            self.delete_container_contents(account, c)
            self.delete_container(account, c)
        self.backend.delete_account(account, account)

    def delete_account(self, account, only_stats=True, dry=True, silent=False):
        if account not in self.existing_accounts():
            raise NameError('%s does not exist' % account)
        if only_stats:
            print "The following %s's entries will be removed:" % account
            print "Objects: %r" % self.list_all_objects(account)
            print "Groups: %r" \
                % self.backend.get_account_groups(account, account).keys()
            return

        trans = self.backend.wrapper.conn.begin()
        try:
            self._delete_account(account)

            if dry:
                if not silent:
                    print "Skipping database commit."
                trans.rollback()
            else:
                trans.commit()
                if not silent:
                    print "%s is deleted." % account
        except:
            trans.rollback()
            raise

    def create_account(self, account):
        return self.backend._lookup_account(account, create=True)

    def create_update_object(self, account, container, name, content_type,
                             data, meta=None, permissions=None, request_user=None):
        meta = meta or {}
        permissions = permissions or {}
        md5 = hashlib.md5()
        size = 0
        hashmap = []
        for block_data in data_read_iterator(data, self.backend.block_size):
            size += len(block_data)
            hashmap.append(self.backend.put_block(block_data))
            md5.update(block_data)

        checksum = md5.hexdigest().lower()

        request_user = request_user or account
        return self.backend.update_object_hashmap(request_user, account,
                                                  container, name, size,
                                                  content_type, hashmap,
                                                  checksum, 'pithos', meta,
                                                  True, permissions)
