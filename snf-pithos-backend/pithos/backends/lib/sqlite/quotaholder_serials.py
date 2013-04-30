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

from dbworker import DBWorker

class QuotaholderSerial(DBWorker):
    """QuotaholderSerial keeps track of quota holder serials."""

    def __init__(self, **params):
        DBWorker.__init__(self, **params)
        execute = self.execute

        execute(""" create table if not exists qh_serials
                          ( serial bigint primary key) """)

    def get_lower(self, serial):
        """Return entries lower than serial."""

        q = "select serial from qh_serials where serial < ?"
        self.execute(q, (serial,))
        return self.fetchall()

    def lookup(self, serials):
        """Return the registered serials."""

        placeholders = ','.join('?' for _ in serials)
        q = "select serial from qh_serials where serial in (%s)" % placeholders
        return [i[0] for i in self.execute(q, serials).fetchall()]

    def insert_serial(self, serial):
        """Insert a serial."""

        q = "insert or ignore into qh_serials (serial) values (?)"
        return self.execute(q, (serial,)).lastrowid

    def insert_many(self, serials):
        """Insert multiple serials."""

        q = "insert into qh_serials(serial) values (?)"
        self.executemany(q, [(s,) for s in serials])

    def delete_many(self, serials):
        """Delete specified serials."""

        if not serials:
            return
        placeholders = ','.join('?' for _ in serials)
        q = "delete from qh_serials where serial in (%s)" % placeholders
        self.conn.execute(q, serials)
