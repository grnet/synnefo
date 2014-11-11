# -*- coding: utf-8 -*-

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

uenc_encoding = 'UTF-8'


def uenc_set_encoding(encoding=None):
    """Set the default encoding for uenc()

    The encoding specified is saved into a global variable
    in this module, and used as a default for uenc()'s
    encoding argument.

    If the encoding is not specified, the locale category LC_CTYPE
    is queried. If it is not set, then it is set to the user's default.
    The resulting preferred encoding is used.

    The "user's default" is implementation specific, but usually
    it is initialized from the environment variables LC_ALL, LC_CTYPE.

    It is called once during module importing to initialize the default.

    """
    global uenc_encoding

    if encoding is None:
        import locale
        LC_CTYPE = locale.LC_CTYPE
        language, encoding = locale.getlocale(LC_CTYPE)
        if encoding is None:
            # locale="" means "user's default"
            locale.setlocale(locale.LC_CTYPE, locale="")
        encoding = locale.getpreferredencoding()

    uenc_encoding = encoding


def uenc(thing, encoding=None):
    """Encode the argument into a string.

    If the thing is already a string, nothing happens to it.
    If it is a unicode object, it is encoded into a string as
    specified by the encoding argument.
    If the thing is another type of object, str() is called on it.

    If the encoding argument is not specified, the module's default
    is used instead. See uenc_set_encoding() for setting the default.

    """
    if encoding is None:
        encoding = uenc_encoding

    if isinstance(thing, unicode):
        try:
            return thing.encode(encoding)
        except (UnicodeEncodeError, LookupError):
            return repr(thing.encode('UTF-8'))

    return str(thing)


def udec(thing, encoding=None):
    """Decode the argument into a unicode object.

    If the thing is already a unicode object, nothing happens to it.
    If it is a string object, it is decoded into a unicode object as
    specified by the encoding argument.
    If the thing is another type of object, str() is called on it.

    If the encoding argument is not specified, the module's default
    is used instead. See uenc_set_encoding() for setting the default.

    """
    if encoding is None:
        encoding = uenc_encoding

    if isinstance(thing, unicode):
        return thing

    try:
        return thing.decode(encoding)
    except UnicodeDecodeError:
        return repr(thing.decode('ISO-8859-1'))


uenc_set_encoding()
