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
