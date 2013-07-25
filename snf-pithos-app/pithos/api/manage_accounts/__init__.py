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

from pithos.api.util import (get_backend, split_container_object_string,
                             Checksum, NoChecksum)
import re
import os

from functools import wraps


def data_read_iterator(str, size=1024):
    offset = 0
    while True:
        data = str[offset:offset + size]
        offset = offset + size
        if not data:
            break
        yield data


def manage_transactions(lock_container_path=False):
    """Decorator function for ManageAccounts methods."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self.backend.pre_exec(lock_container_path)
            try:
                result = func(self, *args, **kwargs)
            except:
                self.backend.post_exec(False)
                raise
            else:
                dry = kwargs.get('dry', False)
                if dry:
                    self.backend.post_exec(False)
                else:
                    self.backend.post_exec(True)
                return result
        return wrapper
    return decorator


class ManageAccounts():
    def __init__(self):
        self.backend = get_backend()

    def cleanup(self):
        self.backend.close()

    def _existing_accounts(self):
        l = sorted([path for path, _ in self.backend.node.node_accounts()])
        return l

    @manage_transactions()
    def existing_accounts(self):
        return self._existing_accounts()

    @manage_transactions()
    def duplicate_accounts(self):
        accounts = self._existing_accounts()
        duplicates = []
        for i in range(len(accounts)):
            account = accounts[i]
            matcher = re.compile(account, re.IGNORECASE)
            duplicate = filter(matcher.match, (i for i in accounts[i + 1:] if
                                               len(i) == len(account)))
            if duplicate:
                duplicate.insert(0, account)
                duplicates.append(duplicate)
        return duplicates

    def _list_all_containers(self, account, step=10):
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

    @manage_transactions()
    def list_all_containers(self, account, step=10):
        return self._list_all_containers(account, step)

    def _list_all_container_objects(self, account, container, virtual=False):
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

    @manage_transactions()
    def list_all_container_objects(self, account, container, virtual=False):
        return self._list_all_container_objects(account, container, virtual)

    def _list_all_objects(self, account, virtual=False):
        containers = self._list_all_containers(account)
        objects = []
        extend = objects.extend
        for c in containers:
            more = self._list_all_container_objects(account, c,
                                                    virtual=virtual)
            extend([os.path.join(c, i) for i in more])
        return objects

    @manage_transactions()
    def list_all_objects(self, account, virtual=False):
        return self._list_all_objects(account, virtual)

    def _list_past_versions(self, account, container, name):
        versions = self.backend.list_versions(account, account, container,
                                              name)
        # do not return the current version
        return list(x[0] for x in versions[:-1])

    @manage_transactions()
    def list_past_versions(self, account, container, name):
        return self._list_past_versions(account, container, name)

    @manage_transactions(lock_container_path=True)
    def move_object(self, src_account, src_container, src_name, dest_account,
                    dry=True, silent=False):
        if src_account not in self._existing_accounts():
            raise NameError('%s does not exist' % src_account)
        if dest_account not in self._existing_accounts():
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
        versions = self._list_past_versions(src_account, src_container,
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
            for path in self._list_all_objects(src_account):
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

    @manage_transactions(lock_container_path=True)
    def merge_account(self, src_account, dest_account, only_stats=True,
                      dry=True, silent=False, delete_src=False):
        if src_account not in self._existing_accounts():
            raise NameError('%s does not exist' % src_account)
        if dest_account not in self._existing_accounts():
            raise NameError('%s does not exist' % dest_account)

        if only_stats:
            print "The following %s's entries will be moved to %s:" \
                % (src_account, dest_account)
            print "Objects: %r" % self._list_all_objects(src_account)
            print "Groups: %r" \
                % self.backend.get_account_groups(src_account,
                                                  src_account).keys()
            return
        self._merge_account(src_account, dest_account, delete_src)

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

    def _delete_container_contents(self, account, container):
        self.backend.delete_container(account, account, container,
                                      delimiter='/')

    @manage_transactions(lock_container_path=True)
    def delete_container_contents(self, account, container):
        return self._delete_container(account, account, container,
                                      delimiter='/')

    def _delete_container(self, account, container):
        self.backend.delete_container(account, account, container)

    @manage_transactions(lock_container_path=True)
    def delete_container(self, account, container):
        self._delete_container(account, account, container)

    def _delete_account(self, account):
        for c in self._list_all_containers(account):
            self._delete_container_contents(account, c)
            self._delete_container(account, c)
        self.backend.delete_account(account, account)

    @manage_transactions(lock_container_path=True)
    def delete_account(self, account, only_stats=True, dry=True, silent=False):
        if account not in self._existing_accounts():
            raise NameError('%s does not exist' % account)
        if only_stats:
            print "The following %s's entries will be removed:" % account
            print "Objects: %r" % self._list_all_objects(account)
            print "Groups: %r" \
                % self.backend.get_account_groups(account, account).keys()
            return
        self._delete_account(account)

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

    @manage_transactions(lock_container_path=True)
    def create_account(self, account):
        return self.backend._lookup_account(account, create=True)

    @manage_transactions(lock_container_path=True)
    def create_update_object(self, account, container, name, content_type,
                             data, meta=None, permissions=None,
                             request_user=None,
                             checksum_compute_class=NoChecksum):
        meta = meta or {}
        permissions = permissions or {}

        assert checksum_compute_class in (
            NoChecksum, Checksum), 'Invalid checksum_compute_class'
        checksum_compute = checksum_compute_class()
        size = 0
        hashmap = []
        for block_data in data_read_iterator(data, self.backend.block_size):
            size += len(block_data)
            hashmap.append(self.backend.put_block(block_data))
            checksum_compute.update(block_data)

        checksum = checksum_compute.hexdigest()

        request_user = request_user or account
        return self.backend.update_object_hashmap(request_user, account,
                                                  container, name, size,
                                                  content_type, hashmap,
                                                  checksum, 'pithos', meta,
                                                  True, permissions)
