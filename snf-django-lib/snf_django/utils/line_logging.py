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
