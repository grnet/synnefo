# Copyright (C) 2012, 2013 GRNET S.A. All rights reserved.
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


class AstakosClientException(Exception):
    def __init__(self, message, status=0):
        self.message = message
        self.status = status

    def __str__(self):
        return repr(self.message)


class BadRequest(AstakosClientException):
    def __init__(self, message):
        """400 Bad Request"""
        super(BadRequest, self).__init__(message, 400)


class Unauthorized(AstakosClientException):
    def __init__(self, message):
        """401 Invalid X-Auth-Token"""
        super(Unauthorized, self).__init__(message, 401)


class Forbidden(AstakosClientException):
    def __init__(self, message):
        """403 Forbidden"""
        super(Forbidden, self).__init__(message, 403)


class NotFound(AstakosClientException):
    def __init__(self, message):
        """404 Not Found"""
        super(NotFound, self).__init__(message, 404)


class NoDisplayName(AstakosClientException):
    def __init__(self, uuid):
        """No display name for the given uuid"""
        message = "No display name for the given uuid: %s" % uuid
        super(NoDisplayName, self).__init__(message)


class NoUUID(AstakosClientException):
    def __init__(self, display_name):
        """No uuid for the given display name"""
        message = "No uuid for the given display name: %s" % display_name
        super(NoUUID, self).__init__(message)
