# Copyright 2014 GRNET S.A. All rights reserved.
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

import logging


class NewlineStreamHandler(logging.StreamHandler):
    """A StreamHandler with configurable message terminator

    When StreamHandler writes a formatted log message to its stream, it
    adds a newline terminator. This behavior is inherited by FileHandler
    and the other classes which derive from it (such as the rotating file
    handlers).

    Starting with Python 3.2, the message terminator will be configurable.
    This has been done by adding a terminator attribute to StreamHandler,
    which when emitting an event now writes the formatted message to its
    stream first, and then writes the terminator. If you don't want
    newline termination for a handler, just set the handler instance's
    terminator attribute to the empty string.

    This is the StreamHandler class from python 3.2

    """
    terminator = '\n'

    def __init__(self, stream=None):
        """Initialize the handler."""
        super(NewlineStreamHandler, self).__init__(stream)

    def flush(self):
        """Flushes the stream."""
        if self.stream and hasattr(self.stream, "flush"):
            self.stream.flush()

    def emit(self, record):
        """Emit a record.

        If a formatter is specified, it is used to format the record.
        The record is then written to the stream with a trailing newline. If
        exception information is present, it is formatted using
        traceback.print_exception and appended to the stream. If the stream
        has an 'encoding' attribute, it is used to determine how to do the
        output to the stream.
        """
        try:
            msg = self.format(record)
            stream = self.stream
            stream.write(msg)
            stream.write(self.terminator)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)
