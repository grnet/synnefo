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

""" Module implementing connection and communication with an AMQP broker.

AMQP Client's instatiated by this module silenty detect connection failures and
try to reconnect to any available broker. Also publishing takes advantage of
publisher-confirms in order to guarantee that messages are properly delivered
to the broker.

"""

from synnefo import settings

if settings.AMQP_BACKEND == 'puka':
    from amqp_puka import AMQPPukaClient as Client
elif settings.AMQP_BACKEND == 'haigha':
    from amqp_haigha import AMQPHaighaClient as Client
else:
    raise Exception('Unknown Backend %s' % settings.AMQP_BACKEND)


class AMQPClient(object):
    """
    AMQP generic client implementing most of the basic AMQP operations.

    This class will create an object of AMQPPukaClient or AMQPHaigha client
    depending on AMQP_BACKEND setting
    """
    def __new__(cls, *args, **kwargs):
        return Client(*args, **kwargs)
