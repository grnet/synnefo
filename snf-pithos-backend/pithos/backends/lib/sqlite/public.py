# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from dbworker import DBWorker

from pithos.backends.random_word import get_random_word

import logging

logger = logging.getLogger(__name__)


class Public(DBWorker):
    """Paths can be marked as public."""

    def __init__(self, **params):
        DBWorker.__init__(self, **params)
        execute = self.execute

        execute(""" create table if not exists public
                          ( public_id integer primary key autoincrement,
                            path      text not null,
                            active    boolean not null default 1,
                            url       text) """)
        execute(""" create unique index if not exists idx_public_path
                    on public(path) """)
        execute(""" create unique index if not exists idx_public_url
                    on public(url) """)

    def get_unique_url(self, public_url_security, public_url_alphabet):
        l = public_url_security
        while 1:
            candidate = get_random_word(length=l, alphabet=public_url_alphabet)
            if self.public_path(candidate) is None:
                return candidate
            l += 1

    def public_set(self, path, public_url_security, public_url_alphabet):
        q = "select public_id from public where path = ?"
        self.execute(q, (path,))
        row = self.fetchone()

        if not row:
            url = self.get_unique_url(
                public_url_security, public_url_alphabet
            )
            q = "insert into public(path, active, url) values(?, 1, ?)"
            self.execute(q, (path, url))
            logger.info('Public url set for path: %s' % path)

    def public_unset(self, path):
        q = "delete from public where path = ?"
        c = self.execute(q, (path,))
        if c.rowcount != 0:
            logger.info('Public url unset for path: %s' % path)

    def public_unset_bulk(self, paths):
        placeholders = ','.join('?' for path in paths)
        q = "delete from public where path in (%s)" % placeholders
        self.execute(q, paths)

    def public_get(self, path):
        q = "select url from public where path = ? and active = 1"
        self.execute(q, (path,))
        row = self.fetchone()
        if row:
            return row[0]
        return None

    def public_list(self, prefix):
        q = ("select path, url from public where "
             "path like ? escape '\\' and active = 1")
        self.execute(q, (self.escape_like(prefix) + '%',))
        return self.fetchall()

    def public_path(self, public):
        q = "select path from public where url = ? and active = 1"
        self.execute(q, (public,))
        row = self.fetchone()
        if row:
            return row[0]
        return None
