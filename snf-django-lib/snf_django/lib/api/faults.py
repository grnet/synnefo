# Copyright 2012, 2013 GRNET S.A. All rights reserved.
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


"""Common API faults."""


def camelCase(s):
    return s[0].lower() + s[1:]


class Fault(Exception):
    def __init__(self, message='', details='', name=''):
        Exception.__init__(self, message, details, name)
        self.message = message
        self.details = details
        self.name = name or camelCase(self.__class__.__name__)


# 2xx
class NotModified(Fault):
    code = 304


# 4xx
class BadRequest(Fault):
    code = 400


class Unauthorized(Fault):
    code = 401


class ResizeNotAllowed(Fault):
    code = 403


class Forbidden(Fault):
    code = 403


class ResizeNotAllowed(Forbidden):
    pass


class ItemNotFound(Fault):
    code = 404


class Conflict(Fault):
    code = 409


class BuildInProgress(Conflict):
    pass


class LengthRequired(Fault):
    code = 411


class PreconditionFailed(Fault):
    code = 412


class RequestEntityTooLarge(Fault):
    code = 413


class OverLimit(RequestEntityTooLarge):
    pass


class BadMediaType(Fault):
    code = 415


class RangeNotSatisfiable(Fault):
    code = 416


class NetworkInUse(Fault):
    code = 421


class UnprocessableEntity(Fault):
    code = 422


# 5xx
class InternalServerError(Fault):
    code = 500


class NotImplemented(Fault):
    code = 501


class ServiceUnavailable(Fault):
    code = 503
