# -*- coding: utf-8 -*-

# Copyright 2013 GRNET S.A. All rights reserved.
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
        return thing.encode(encoding)

    return str(thing)

uenc_set_encoding()

