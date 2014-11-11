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


"""Common API faults."""


def camel_case(s):
    return s[0].lower() + s[1:]


class Fault(Exception):
    def __init__(self, message='', details='', name='', code=500):
        self.message = message
        self.details = details
        if not hasattr(self, 'code'):
            self.code = code
        self.name = name or camel_case(self.__class__.__name__)
        Exception.__init__(self, message, details, self.name, self.code)


# 2xx
class NotModified(Fault):
    code = 304


# 4xx
class BadRequest(Fault):
    code = 400


class Unauthorized(Fault):
    code = 401


class Forbidden(Fault):
    code = 403


class ResizeNotAllowed(Forbidden):
    pass


class NotAllowed(Fault):
    code = 405

    def __init__(self, message='', details='', name='', code=500,
                 allowed_methods=None):
        """
        :param allowed_methods: (list) the valid methods
        """
        super(NotAllowed, self).__init__(message, details, name, code)
        self.allowed_methods = allowed_methods or []


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
