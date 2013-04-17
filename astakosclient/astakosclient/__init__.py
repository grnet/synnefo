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

import logging
import urlparse
import urllib
import hashlib
from copy import copy

import simplejson
from astakosclient.utils import \
    retry, scheme_to_class, parse_request, check_input
from astakosclient.errors import \
    AstakosClientException, Unauthorized, BadRequest, NotFound, Forbidden, \
    NoUserName, NoUUID, BadValue, QuotaLimit, InvalidResponse


# --------------------------------------------------------------------
# Astakos Client Class

def get_token_from_cookie(request, cookie_name):
    """Extract token from the cookie name provided

    Cookie should be in the same form as astakos
    service sets its cookie contents:
        <user_uniq>|<user_token>

    """
    try:
        cookie_content = urllib.unquote(request.COOKIE.get(cookie_name, None))
        return cookie_content.split("|")[1]
    except:
        return None


class AstakosClient():
    """AstakosClient Class Implementation"""

    # ----------------------------------
    def __init__(self, astakos_url, retry=0,
                 use_pool=False, pool_size=8, logger=None):
        """Initialize AstakosClient Class

        Keyword arguments:
        astakos_url -- i.e https://accounts.example.com (string)
        use_pool    -- use objpool for http requests (boolean)
        retry       -- how many time to retry (integer)
        logger      -- pass a different logger

        """
        if logger is None:
            logging.basicConfig(
                format='%(asctime)s [%(levelname)s] %(name)s %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
                level=logging.INFO)
            logger = logging.getLogger("astakosclient")
        logger.debug("Intialize AstakosClient: astakos_url = %s, "
                     "use_pool = %s" % (astakos_url, use_pool))

        check_input("__init__", logger, astakos_url=astakos_url)

        # Check for supported scheme
        p = urlparse.urlparse(astakos_url)
        conn_class = scheme_to_class(p.scheme, use_pool, pool_size)
        if conn_class is None:
            m = "Unsupported scheme: %s" % p.scheme
            logger.error(m)
            raise BadValue(m)

        # Save astakos_url etc. in our class
        self.retry = retry
        self.logger = logger
        self.netloc = p.netloc
        self.scheme = p.scheme
        self.conn_class = conn_class

    # ----------------------------------
    @retry
    def _call_astakos(self, token, request_path,
                      headers=None, body=None, method="GET"):
        """Make the actual call to Astakos Service"""
        if token is not None:
            hashed_token = hashlib.sha1()
            hashed_token.update(token)
            using_token = "using token %s" % (hashed_token.hexdigest())
        else:
            using_token = "without using token"
        self.logger.debug(
            "Make a %s request to %s %s with headers %s and body %s"
            % (method, request_path, using_token, headers, body))

        # Check Input
        if headers is None:
            headers = {}
        if body is None:
            body = {}
        if request_path[0] != '/':
            request_path = "/" + request_path

        # Build request's header and body
        kwargs = {}
        kwargs['headers'] = copy(headers)
        if token is not None:
            kwargs['headers']['X-Auth-Token'] = token
        if body:
            kwargs['body'] = copy(body)
            kwargs['headers'].setdefault(
                'content-type', 'application/octet-stream')
        kwargs['headers'].setdefault('content-length',
                                     len(body) if body else 0)

        try:
            # Get the connection object
            with self.conn_class(self.netloc) as conn:
                # Send request
                (message, data, status) = \
                    _do_request(conn, method, request_path, **kwargs)
        except Exception as err:
            self.logger.error("Failed to send request: %s" % repr(err))
            raise AstakosClientException(str(err))

        # Return
        self.logger.debug("Request returned with status %s" % status)
        if status == 400:
            raise BadRequest(message, data)
        elif status == 401:
            raise Unauthorized(message, data)
        elif status == 403:
            raise Forbidden(message, data)
        elif status == 404:
            raise NotFound(message, data)
        elif status < 200 or status >= 300:
            raise AstakosClientException(message, data, status)

        try:
            if data:
                return simplejson.loads(unicode(data))
            else:
                return None
        except Exception as err:
            self.logger.error("Cannot parse response \"%s\" with simplejson: %s"
                              % (data, str(err)))
            raise InvalidResponse(str(err), data)

    # ------------------------
    # GET /im/authenticate
    def get_user_info(self, token, usage=False):
        """Authenticate user and get user's info as a dictionary

        Keyword arguments:
        token   -- user's token (string)
        usage   -- return usage information for user (boolean)

        In case of success return user information (json parsed format).
        Otherwise raise an AstakosClientException.

        """
        # Send request
        auth_path = "/im/authenticate"
        if usage:
            auth_path += "?usage=1"
        return self._call_astakos(token, auth_path)

    # ----------------------------------
    # POST /user_catalogs (or /service/api/user_catalogs)
    #   with {'uuids': uuids}
    def _uuid_catalog(self, token, uuids, req_path):
        req_headers = {'content-type': 'application/json'}
        req_body = parse_request({'uuids': uuids}, self.logger)
        data = self._call_astakos(
            token, req_path, req_headers, req_body, "POST")
        if "uuid_catalog" in data:
            return data.get("uuid_catalog")
        else:
            m = "_uuid_catalog request returned %s. No uuid_catalog found" \
                % data
            self.logger.error(m)
            raise AstakosClientException(m)

    def get_usernames(self, token, uuids):
        """Return a uuid_catalog dictionary for the given uuids

        Keyword arguments:
        token   -- user's token (string)
        uuids   -- list of user ids (list of strings)

        The returned uuid_catalog is a dictionary with uuids as
        keys and the corresponding user names as values

        """
        req_path = "/user_catalogs"
        return self._uuid_catalog(token, uuids, req_path)

    def get_username(self, token, uuid):
        """Return the user name of a uuid (see get_usernames)"""
        check_input("get_username", self.logger, uuid=uuid)
        uuid_dict = self.get_usernames(token, [uuid])
        if uuid in uuid_dict:
            return uuid_dict.get(uuid)
        else:
            raise NoUserName(uuid)

    def service_get_usernames(self, token, uuids):
        """Return a uuid_catalog dict using a service's token"""
        req_path = "/service/api/user_catalogs"
        return self._uuid_catalog(token, uuids, req_path)

    def service_get_username(self, token, uuid):
        """Return the displayName of a uuid using a service's token"""
        check_input("service_get_username", self.logger, uuid=uuid)
        uuid_dict = self.service_get_usernames(token, [uuid])
        if uuid in uuid_dict:
            return uuid_dict.get(uuid)
        else:
            raise NoUserName(uuid)

    # ----------------------------------
    # POST /user_catalogs (or /service/api/user_catalogs)
    #   with {'displaynames': display_names}
    def _displayname_catalog(self, token, display_names, req_path):
        req_headers = {'content-type': 'application/json'}
        req_body = parse_request({'displaynames': display_names}, self.logger)
        data = self._call_astakos(
            token, req_path, req_headers, req_body, "POST")
        if "displayname_catalog" in data:
            return data.get("displayname_catalog")
        else:
            m = "_displayname_catalog request returned %s. " \
                "No displayname_catalog found" % data
            self.logger.error(m)
            raise AstakosClientException(m)

    def get_uuids(self, token, display_names):
        """Return a displayname_catalog for the given names

        Keyword arguments:
        token           -- user's token (string)
        display_names   -- list of user names (list of strings)

        The returned displayname_catalog is a dictionary with
        the names as keys and the corresponding uuids as values

        """
        req_path = "/user_catalogs"
        return self._displayname_catalog(token, display_names, req_path)

    def get_uuid(self, token, display_name):
        """Return the uuid of a name (see getUUIDs)"""
        check_input("get_uuid", self.logger, display_name=display_name)
        name_dict = self.get_uuids(token, [display_name])
        if display_name in name_dict:
            return name_dict.get(display_name)
        else:
            raise NoUUID(display_name)

    def service_get_uuids(self, token, display_names):
        """Return a display_name catalog using a service's token"""
        req_path = "/service/api/user_catalogs"
        return self._displayname_catalog(token, display_names, req_path)

    def service_get_uuid(self, token, display_name):
        """Return the uuid of a name using a service's token"""
        check_input("service_get_uuid", self.logger, display_name=display_name)
        name_dict = self.service_get_uuids(token, [display_name])
        if display_name in name_dict:
            return name_dict.get(display_name)
        else:
            raise NoUUID(display_name)

    # ----------------------------------
    # GET "/im/get_services"
    def get_services(self):
        """Return a list of dicts with the registered services"""
        return self._call_astakos(None, "/im/get_services")

    # ----------------------------------
    # GET "/astakos/api/resources"
    def get_resources(self):
        """Return a dict of dicts with the available resources"""
        return self._call_astakos(None, "/astakos/api/resources")

    # ----------------------------------
    # GET "/astakos/api/quotas"
    def get_quotas(self, token):
        """Get user's quotas

        Keyword arguments:
        token   -- user's token (string)

        In case of success return a dict of dicts with user's current quotas.
        Otherwise raise an AstakosClientException

        """
        return self._call_astakos(token, "/astakos/api/quotas")

    # ----------------------------------
    # GET "/astakos/api/service_quotas"
    def service_get_quotas(self, token, user=None):
        """Get all quotas for resources associated with the service

        Keyword arguments:
        token   -- service's token (string)
        user    -- optionally, the uuid of a specific user

        In case of success return a dict of dicts of dicts with current quotas
        for all users, or of a specified user, if user argument is set.
        Otherwise raise an AstakosClientException

        """
        query = "/astakos/api/service_quotas"
        if user is not None:
            query += "?user=" + user
        return self._call_astakos(token, query)

    # ----------------------------------
    # POST "/astakos/api/commisions"
    def issue_commission(self, token, request):
        """Issue a commission

        Keyword arguments:
        token   -- service's token (string)
        request -- commision request (dict)

        In case of success return commission's id (int).
        Otherwise raise an AstakosClientException.

        """
        req_headers = {'content-type': 'application/json'}
        req_body = parse_request(request, self.logger)
        try:
            response = self._call_astakos(token, "/astakos/api/commissions",
                                          req_headers, req_body, "POST")
        except AstakosClientException as err:
            if err.status == 413:
                raise QuotaLimit(err.message, err.details)
            else:
                raise

        if "serial" in response:
            return response['serial']
        else:
            m = "issue_commission_core request returned %s. No serial found" \
                % response
            self.logger.error(m)
            raise AstakosClientException(m)

    def issue_one_commission(self, token, holder, source, provisions,
                             name="", force=False, auto_accept=False):
        """Issue one commission (with specific holder and source)

        keyword arguments:
        token       -- service's token (string)
        holder      -- user's id (string)
        source      -- commission's source (ex system) (string)
        provisions  -- resources with their quantity (list of (string, int))
        name        -- description of the commission (string)
        force       -- force this commission (boolean)
        auto_accept -- auto accept this commission (boolean)

        In case of success return commission's id (int).
        Otherwise raise an AstakosClientException.
        (See also issue_commission)

        """
        check_input("issue_one_commission", self.logger,
                    holder=holder, source=source,
                    provisions=provisions)

        request = {}
        request["force"] = force
        request["auto_accept"] = auto_accept
        request["name"] = name
        try:
            request["provisions"] = []
            for resource, quantity in provisions.iteritems():
                t = {"holder": holder, "source": source,
                     "resource": resource, "quantity": quantity}
                request["provisions"].append(t)
        except Exception as err:
            self.logger.error(str(err))
            raise BadValue(str(err))

        return self.issue_commission(token, request)

    # ----------------------------------
    # GET "/astakos/api/commissions"
    def get_pending_commissions(self, token):
        """Get Pending Commissions

        Keyword arguments:
        token   -- service's token (string)

        In case of success return a list of pending commissions' ids
        (list of integers)

        """
        return self._call_astakos(token, "/astakos/api/commissions")

    # ----------------------------------
    # GET "/astakos/api/commissions/<serial>
    def get_commission_info(self, token, serial):
        """Get Description of a Commission

        Keyword arguments:
        token   -- service's token (string)
        serial  -- commission's id (int)

        In case of success return a dict of dicts containing
        informations (details) about the requested commission

        """
        check_input("get_commission_info", self.logger, serial=serial)

        path = "/astakos/api/commissions/" + str(serial)
        return self._call_astakos(token, path)

    # ----------------------------------
    # POST "/astakos/api/commissions/<serial>/action"
    def commission_action(self, token, serial, action):
        """Perform a commission action

        Keyword arguments:
        token   -- service's token (string)
        serial  -- commission's id (int)
        action  -- action to perform, currently accept/reject (string)

        In case of success return nothing.

        """
        check_input("commission_action", self.logger,
                    serial=serial, action=action)

        path = "/astakos/api/commissions/" + str(serial) + "/action"
        req_headers = {'content-type': 'application/json'}
        req_body = parse_request({str(action): ""}, self.logger)
        self._call_astakos(token, path, req_headers, req_body, "POST")

    def accept_commission(self, token, serial):
        """Accept a commission (see commission_action)"""
        self.commission_action(token, serial, "accept")

    def reject_commission(self, token, serial):
        """Reject a commission (see commission_action)"""
        self.commission_action(token, serial, "reject")

    # ----------------------------------
    # POST "/astakos/api/commissions/action"
    def resolve_commissions(self, token, accept_serials, reject_serials):
        """Resolve multiple commissions at once

        Keyword arguments:
        token           -- service's token (string)
        accept_serials  -- commissions to accept (list of ints)
        reject_serials  -- commissions to reject (list of ints)

        In case of success return a dict of dicts describing which
        commissions accepted, which rejected and which failed to
        resolved.

        """
        check_input("resolve_commissions", self.logger,
                    accept_serials=accept_serials,
                    reject_serials=reject_serials)

        path = "/astakos/api/commissions/action"
        req_headers = {'content-type': 'application/json'}
        req_body = parse_request({"accept": accept_serials,
                                  "reject": reject_serials},
                                 self.logger)
        return self._call_astakos(token, path, req_headers, req_body, "POST")


# --------------------------------------------------------------------
# Private functions
# We want _doRequest to be a distinct function
# so that we can replace it during unit tests.
def _do_request(conn, method, url, **kwargs):
    """The actual request. This function can easily be mocked"""
    conn.request(method, url, **kwargs)
    response = conn.getresponse()
    length = response.getheader('content-length', None)
    data = response.read(length)
    status = int(response.status)
    message = response.reason
    return (message, data, status)
