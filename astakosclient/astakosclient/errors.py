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

"""
Astakos Client Exceptions
"""


class AstakosClientException(Exception):
    """Base AstakosClientException Class"""
    def __init__(self, message='', details='', status=500):
        self.message = message
        self.details = details
        if not hasattr(self, 'status'):
            self.status = status
        super(AstakosClientException,
              self).__init__(self.message, self.details, self.status)


class BadValue(AstakosClientException):
    """Re-define ValueError Exception under AstakosClientException"""
    def __init__(self, details):
        message = "ValueError"
        super(BadValue, self).__init__(message, details)


class InvalidResponse(AstakosClientException):
    """Return simplejson parse Exception as AstakosClient one"""
    def __init__(self, message, details):
        super(InvalidResponse, self).__init__(message, details)


class BadRequest(AstakosClientException):
    """BadRequest Exception"""
    status = 400


class Unauthorized(AstakosClientException):
    """Unauthorized Exception"""
    status = 401


class Forbidden(AstakosClientException):
    """Forbidden Exception"""
    status = 403


class NotFound(AstakosClientException):
    """NotFound Exception"""
    status = 404


class QuotaLimit(AstakosClientException):
    """QuotaLimit Exception"""
    status = 413


class NoUserName(AstakosClientException):
    """No display name for the given uuid"""
    def __init__(self, uuid):
        message = "No display name for the given uuid: %s" % uuid
        super(NoUserName, self).__init__(message)


class NoUUID(AstakosClientException):
    """No uuid for the given display name"""
    def __init__(self, display_name):
        message = "No uuid for the given display name: %s" % display_name
        super(NoUUID, self).__init__(message)


class NoEndpoints(AstakosClientException):
    """No endpoints found matching the criteria given"""
    def __init__(self, ep_name, ep_type, ep_region, ep_version_id):
        message = "No endpoints found matching" + \
                  (", name = %s" % ep_name) if ep_name is not None else "" + \
                  (", type = %s" % ep_type) if ep_type is not None else "" + \
                  (", region = %s" % ep_region) \
                  if ep_region is not None else "" + \
                  (", version_id = %s" % ep_version_id) \
                  if ep_version_id is not None else "."
        super(NoEndpoints, self).__init__(message)
