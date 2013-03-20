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

import os
import sqlite3
import sys

from os.path import exists, expanduser, isdir, isfile, join, split
from shutil import copyfile
from time import time

from pithos.tools.lib.transfer import download, upload
from pithos.tools.lib.client import Pithos_Client, Fault
from pithos.tools.lib.hashmap import merkle
from pithos.tools.lib.util import get_user, get_auth, get_url


DEFAULT_CONTAINER = 'pithos'
SETTINGS_DIR = expanduser('~/.pithos')
TRASH_DIR = '.pithos_trash'

SQL_CREATE_FILES_TABLE = '''CREATE TABLE IF NOT EXISTS files (
                                path TEXT PRIMARY KEY,
                                hash TEXT,
                                timestamp INTEGER)'''


client = Pithos_Client(get_url(), get_auth(), get_user())


def _makedirs(path):
    try:
        os.makedirs(path)
    except OSError:
        pass


class State(object):
    def __init__(self, syncdir, container):
        self.syncdir = syncdir
        self.container = container
        self.trashdir = join(syncdir, TRASH_DIR)
        self.deleted_dirs = set()

        _makedirs(self.trashdir)

        dbpath = join(SETTINGS_DIR, 'sync.db')
        self.conn = sqlite3.connect(dbpath)
        self.conn.execute(SQL_CREATE_FILES_TABLE)
        self.conn.commit()

    def current_hash(self, path):
        """Return the hash of the file as it exists now in the filesystem"""

        fullpath = join(self.syncdir, path)
        if fullpath in self.deleted_dirs:
            return 'DEL'
        if not exists(fullpath):
            return 'DEL'
        if isdir(fullpath):
            return 'DIR'
        return merkle(fullpath)

    def delete_inactive(self, timestamp):
        sql = 'DELETE FROM files WHERE timestamp != ?'
        self.conn.execute(sql, (timestamp,))
        self.conn.commit()

    def download(self, path, hash):
        fullpath = join(self.syncdir, path)
        if hash == 'DEL':
            self.trash(path)
        elif hash == 'DIR':
            _makedirs(fullpath)
        else:
            self.trash(path)    # Trash any old version
            localpath = self.find_hash(hash)
            if localpath:
                copyfile(localpath, fullpath)
            else:
                print 'Downloading %s...' % path
                download(client, self.container, path, fullpath)

        current = self.current_hash(path)
        assert current == hash, "Downloaded file does not match hash"
        self.save(path, hash)

    def empty_trash(self):
        for filename in os.listdir(self.trashdir):
            path = join(self.trashdir, filename)
            os.remove(path)

    def find_hash(self, hash):
        sql = 'SELECT path FROM files WHERE hash = ?'
        ret = self.conn.execute(sql, (hash,)).fetchone()
        if ret:
            return join(self.syncdir, ret[0])

        if hash in os.listdir(self.trashdir):
            return join(self.trashdir, hash)

        return None

    def previous_hash(self, path):
        """Return the hash of the file according to the previous sync with
           the server. Return DEL if not such entry exists."""

        sql = 'SELECT hash FROM files WHERE path = ?'
        ret = self.conn.execute(sql, (path,)).fetchone()
        return ret[0] if ret else 'DEL'

    def remote_hash(self, path):
        """Return the hash of the file according to the server"""

        try:
            meta = client.retrieve_object_metadata(self.container, path)
        except Fault:
            return 'DEL'
        if meta.get('content-type', '').split(';', 1)[0].strip() == 'application/directory':
            return 'DIR'
        else:
            return meta['x-object-hash']

    def remove_deleted_dirs(self):
        for path in sorted(self.deleted_dirs, key=len, reverse=True):
            os.rmdir(path)
            self.deleted_dirs.remove(path)

    def resolve_conflict(self, path, hash):
        """Resolve a sync conflict by renaming the local file and downloading
           the remote one."""

        fullpath = join(self.syncdir, path)
        resolved = fullpath + '.local'
        i = 0
        while exists(resolved):
            i += 1
            resolved = fullpath + '.local%d' % i

        os.rename(fullpath, resolved)
        self.download(path, hash)

    def rmdir(self, path):
        """Remove a dir or mark for deletion if non-empty

        If a dir is empty delete it and check if any of its parents should be
        deleted too. Else mark it for later deletion.
        """

        fullpath = join(self.syncdir, path)
        if not exists(fullpath):
            return

        if os.listdir(fullpath):
            # Directory not empty
            self.deleted_dirs.add(fullpath)
            return

        os.rmdir(fullpath)
        self.deleted_dirs.discard(fullpath)

        parent = dirname(fullpath)
        while parent in self.deleted_dirs:
            os.rmdir(parent)
            self.deleted_dirs.remove(parent)
            parent = dirname(parent)

    def save(self, path, hash):
        """Save the hash value of a file. This value will be later returned
           by `previous_hash`."""

        sql = 'INSERT OR REPLACE INTO files (path, hash) VALUES (?, ?)'
        self.conn.execute(sql, (path, hash))
        self.conn.commit()

    def touch(self, path, now):
        sql = 'UPDATE files SET timestamp = ? WHERE path = ?'
        self.conn.execute(sql, (now, path))
        self.conn.commit()

    def trash(self, path):
        """Move a file to trash or delete it if it's a directory"""

        fullpath = join(self.syncdir, path)
        if not exists(fullpath):
            return

        if isfile(fullpath):
            hash = merkle(fullpath)
            trashpath = join(self.trashdir, hash)
            os.rename(fullpath, trashpath)
        else:
            self.rmdir(path)

    def upload(self, path, hash):
        fullpath = join(self.syncdir, path)
        if hash == 'DEL':
            client.delete_object(self.container, path)
        elif hash == 'DIR':
            client.create_directory_marker(self.container, path)
        else:
            prefix, name = split(path)
            if prefix:
                prefix += '/'
            print 'Uploading %s...' % path
            upload(client, fullpath, self.container, prefix, name)

        remote = self.remote_hash(path)
        assert remote == hash, "Uploaded file does not match hash"
        self.save(path, hash)


def sync(path, state):
    previous = state.previous_hash(path)
    current = state.current_hash(path)
    remote = state.remote_hash(path)

    if current == previous:
        # No local changes, download any remote changes
        if remote != previous:
            state.download(path, remote)
    elif remote == previous:
        # No remote changes, upload any local changes
        if current != previous:
            state.upload(path, current)
    else:
        # Both local and remote file have changes since last sync
        if current == remote:
            state.save(path, remote)    # Local and remote changes match
        else:
            state.resolve_conflict(path, remote)


def walk(dir, container):
    """Iterates on the files of the hierarchy created by merging the files
       in `dir` and the objects in `container`."""

    pending = ['']

    while pending:
        dirs = set()
        files = set()
        root = pending.pop(0)   # Depth First Traversal
        if root == TRASH_DIR:
            continue
        if root:
            yield root

        dirpath = join(dir, root)
        if exists(dirpath):
            for filename in os.listdir(dirpath):
                path = join(root, filename)
                if isdir(join(dir, path)):
                    dirs.add(path)
                else:
                    files.add(path)

        for object in client.list_objects(container, format='json',
                                          prefix=root, delimiter='/'):
            if 'subdir' in object:
                continue
            name = object['name']
            if object['content_type'].split(';', 1)[0].strip() == 'application/directory':
                dirs.add(name)
            else:
                files.add(name)

        pending += sorted(dirs)
        for path in files:
            yield path


def main():
    if len(sys.argv) != 2:
        print 'syntax: %s <dir>' % sys.argv[0]
        sys.exit(1)

    syncdir = sys.argv[1]

    _makedirs(SETTINGS_DIR)
    container = os.environ.get('PITHOS_SYNC_CONTAINER', DEFAULT_CONTAINER)
    client.create_container(container)

    state = State(syncdir, container)

    now = int(time())
    for path in walk(syncdir, container):
        print 'Syncing', path
        sync(path, state)
        state.touch(path, now)

    state.delete_inactive(now)
    state.empty_trash()
    state.remove_deleted_dirs()


if __name__ == '__main__':
    main()
