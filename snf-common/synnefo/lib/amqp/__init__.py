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
