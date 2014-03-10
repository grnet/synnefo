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

from sqlalchemy import Table, Column, MetaData
from sqlalchemy.types import BigInteger
from sqlalchemy.sql import select
from sqlalchemy.exc import NoSuchTableError

from dbworker import DBWorker


def create_tables(engine):
    metadata = MetaData()
    columns = []
    columns.append(Column('serial', BigInteger, primary_key=True))
    Table('qh_serials', metadata, *columns, mysql_engine='InnoDB')

    metadata.create_all(engine)
    return metadata.sorted_tables


class QuotaholderSerial(DBWorker):
    """QuotaholderSerial keeps track of quota holder serials.
    """

    def __init__(self, **params):
        DBWorker.__init__(self, **params)
        try:
            metadata = MetaData(self.engine)
            self.qh_serials = Table('qh_serials', metadata, autoload=True)
        except NoSuchTableError:
            tables = create_tables(self.engine)
            map(lambda t: self.__setattr__(t.name, t), tables)

    def get_lower(self, serial):
        """Return entries lower than serial."""

        s = select([self.qh_serials.c.serial])
        s = s.where(self.qh_serials.c.serial < serial)
        r = self.conn.execute(s)
        rows = r.fetchall()
        r.close()
        return rows

    def lookup(self, serials):
        """Return the registered serials."""

        if not serials:
            return []
        s = select([self.qh_serials.c.serial])
        s = s.where(self.qh_serials.c.serial.in_(serials))
        r = self.conn.execute(s)
        rows = r.fetchall()
        r.close()
        return [row[0] for row in rows]

    def insert_serial(self, serial):
        """Insert a serial.
        """

        s = self.qh_serials.insert()
        r = self.conn.execute(s, serial=serial)
        r.close()

    def insert_many(self, serials):
        """Insert multiple serials.
        """

        r = self.conn.execute(
            self.qh_serials.insert(),
            list({'serial': s} for s in serials)
        )
        r.close()

    def delete_many(self, serials):
        if not serials:
            return
        st = self.qh_serials.delete().where(
            self.qh_serials.c.serial.in_(serials)
        )
        self.conn.execute(st).close()
