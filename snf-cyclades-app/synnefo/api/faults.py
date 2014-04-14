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


def camelCase(s):
    return s[0].lower() + s[1:]


class Fault(Exception):
    def __init__(self, message='', details='', name=''):
        Exception.__init__(self, message, details, name)
        self.message = message
        self.details = details
        self.name = name or camelCase(self.__class__.__name__)


class BadRequest(Fault):
    code = 400


class Unauthorized(Fault):
    code = 401


class ResizeNotAllowed(Fault):
    code = 403


class Forbidden(Fault):
    code = 403


class ItemNotFound(Fault):
    code = 404


class BuildInProgress(Fault):
    code = 409


class OverLimit(Fault):
    code = 413


class BadMediaType(Fault):
    code = 415


class NetworkInUse(Fault):
    code = 421


class ServiceUnavailable(Fault):
    code = 503
