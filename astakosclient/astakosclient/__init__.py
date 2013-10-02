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
Simple and minimal client for the Astakos authentication service
"""

import logging
import urlparse
import urllib
import hashlib
from copy import copy

import simplejson
from astakosclient.utils import \
    retry_dec, scheme_to_class, parse_request, check_input, join_urls
from astakosclient.errors import \
    AstakosClientException, Unauthorized, BadRequest, NotFound, Forbidden, \
    NoUserName, NoUUID, BadValue, QuotaLimit, InvalidResponse, NoEndpoints


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
    except BaseException:
        return None


# Too many instance attributes. pylint: disable-msg=R0902
# Too many public methods. pylint: disable-msg=R0904
class AstakosClient(object):
    """AstakosClient Class Implementation"""

    # ----------------------------------
    # Initialize AstakosClient Class
    # Too many arguments. pylint: disable-msg=R0913
    # Too many local variables. pylint: disable-msg=R0914
    # Too many statements. pylint: disable-msg=R0915
    def __init__(self, token, auth_url,
                 retry=0, use_pool=False, pool_size=8, logger=None):
        """Initialize AstakosClient Class

        Keyword arguments:
        token       -- user's/service's token (string)
        auth_url    -- i.e https://accounts.example.com/identity/v2.0
        retry       -- how many time to retry (integer)
        use_pool    -- use objpool for http requests (boolean)
        pool_size   -- if using pool, define the pool size
        logger      -- pass a different logger

        """

        # Get logger
        if logger is None:
            logging.basicConfig(
                format='%(asctime)s [%(levelname)s] %(name)s %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
                level=logging.INFO)
            logger = logging.getLogger("astakosclient")
        logger.debug("Intialize AstakosClient: auth_url = %s, "
                     "use_pool = %s, pool_size = %s",
                     auth_url, use_pool, pool_size)

        # Check that token and auth_url (mandatory options) are given
        check_input("__init__", logger, token=token, auth_url=auth_url)

        # Initialize connection class
        parsed_auth_url = urlparse.urlparse(auth_url)
        conn_class = \
            scheme_to_class(parsed_auth_url.scheme, use_pool, pool_size)
        if conn_class is None:
            msg = "Unsupported scheme: %s" % parsed_auth_url.scheme
            logger.error(msg)
            raise BadValue(msg)

        # Save astakos base url, logger, connection class etc in our class
        self.retry = retry
        self.logger = logger
        self.token = token
        self.astakos_base_url = parsed_auth_url.netloc
        self.scheme = parsed_auth_url.scheme
        self.conn_class = conn_class

        # Initialize astakos api prefixes
        # API urls under auth_url
        self.auth_prefix = parsed_auth_url.path
        self.api_tokens = join_urls(self.auth_prefix, "tokens")

        # ------------------------------
        # API urls under account_url
        # Get account_url from get_endpoints
        # get_endpoints needs self.api_tokens
        endpoints = self.get_endpoints(non_authentication=True)
        account_service_catalog = parse_endpoints(
            endpoints, ep_name="astakos_account", ep_version_id="v1.0")
        self.account_url = \
            account_service_catalog[0]['endpoints'][0]['publicURL']
        parsed_account_url = urlparse.urlparse(self.account_url)

        self.account_prefix = parsed_account_url.path
        self.logger.debug("Got account_prefix \"%s\"" % self.account_prefix)

        self.api_authenticate = join_urls(
            self.account_prefix, "authenticate")
        self.api_usercatalogs = join_urls(
            self.account_prefix, "user_catalogs")
        self.api_service_usercatalogs = join_urls(
            self.account_prefix, "service/user_catalogs")
        self.api_resources = join_urls(
            self.account_prefix, "resources")
        self.api_quotas = join_urls(
            self.account_prefix, "quotas")
        self.api_service_quotas = join_urls(
            self.account_prefix, "service_quotas")
        self.api_commissions = join_urls(
            self.account_prefix, "commissions")
        self.api_commissions_action = join_urls(
            self.api_commissions, "action")
        self.api_feedback = join_urls(
            self.account_prefix, "feedback")
        self.api_projects = join_urls(
            self.account_prefix, "projects")
        self.api_applications = join_urls(
            self.api_projects, "apps")
        self.api_memberships = join_urls(
            self.api_projects, "memberships")

        # ------------------------------
        # API urls under ui_url
        # Get ui url from get_endpoints
        # get_endpoints needs self.api_tokens
        ui_service_catalog = parse_endpoints(
            endpoints, ep_name="astakos_account", ep_version_id="v1.0")
        parsed_ui_url = urlparse.urlparse(
            ui_service_catalog[0]['endpoints'][0]['SNF:uiURL'])
        self.ui_url = \
            ui_service_catalog[0]['endpoints'][0]['SNF:uiURL']
        parsed_ui_url = urlparse.urlparse(self.ui_url)

        self.ui_prefix = parsed_ui_url.path
        self.logger.debug("Got ui_prefix \"%s\"" % self.ui_prefix)

        self.api_getservices = join_urls(self.ui_prefix, "get_services")

    # ----------------------------------
    @retry_dec
    def _call_astakos(self, request_path, headers=None,
                      body=None, method="GET", log_body=True):
        """Make the actual call to Astakos Service"""
        hashed_token = hashlib.sha1()
        hashed_token.update(self.token)
        self.logger.debug(
            "Make a %s request to %s, using token with hash %s, "
            "with headers %s and body %s",
            method, request_path, hashed_token.hexdigest(), headers,
            body if log_body else "(not logged)")

        # Check Input
        if headers is None:
            headers = {}
        if body is None:
            body = {}

        # Build request's header and body
        kwargs = {}
        kwargs['headers'] = copy(headers)
        kwargs['headers']['X-Auth-Token'] = self.token
        if body:
            kwargs['body'] = copy(body)
            kwargs['headers'].setdefault(
                'content-type', 'application/octet-stream')
        kwargs['headers'].setdefault('content-length',
                                     len(body) if body else 0)

        try:
            # Get the connection object
            with self.conn_class(self.astakos_base_url) as conn:
                # Send request
                # Used * or ** magic. pylint: disable-msg=W0142
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
            msg = "Cannot parse response \"%s\" with simplejson: %s"
            self.logger.error(msg % (data, str(err)))
            raise InvalidResponse(str(err), data)

    # ------------------------
    # do a GET to ``API_AUTHENTICATE``
    def get_user_info(self, usage=False):
        """Authenticate user and get user's info as a dictionary

        Keyword arguments:
        usage   -- return usage information for user (boolean)

        In case of success return user information (json parsed format).
        Otherwise raise an AstakosClientException.

        """
        # Send request
        auth_path = self.api_authenticate
        if usage:
            auth_path += "?usage=1"
        return self._call_astakos(auth_path)

    # ----------------------------------
    # do a POST to ``API_USERCATALOGS`` (or ``API_SERVICE_USERCATALOGS``)
    #   with {'uuids': uuids}
    def _uuid_catalog(self, uuids, req_path):
        """Helper function to retrieve uuid catalog"""
        req_headers = {'content-type': 'application/json'}
        req_body = parse_request({'uuids': uuids}, self.logger)
        data = self._call_astakos(req_path, headers=req_headers,
                                  body=req_body, method="POST")
        if "uuid_catalog" in data:
            return data.get("uuid_catalog")
        else:
            msg = "_uuid_catalog request returned %s. No uuid_catalog found" \
                  % data
            self.logger.error(msg)
            raise AstakosClientException(msg)

    def get_usernames(self, uuids):
        """Return a uuid_catalog dictionary for the given uuids

        Keyword arguments:
        uuids   -- list of user ids (list of strings)

        The returned uuid_catalog is a dictionary with uuids as
        keys and the corresponding user names as values

        """
        return self._uuid_catalog(uuids, self.api_usercatalogs)

    def get_username(self, uuid):
        """Return the user name of a uuid (see get_usernames)"""
        check_input("get_username", self.logger, uuid=uuid)
        uuid_dict = self.get_usernames([uuid])
        if uuid in uuid_dict:
            return uuid_dict.get(uuid)
        else:
            raise NoUserName(uuid)

    def service_get_usernames(self, uuids):
        """Return a uuid_catalog dict using a service's token"""
        return self._uuid_catalog(uuids, self.api_service_usercatalogs)

    def service_get_username(self, uuid):
        """Return the displayName of a uuid using a service's token"""
        check_input("service_get_username", self.logger, uuid=uuid)
        uuid_dict = self.service_get_usernames([uuid])
        if uuid in uuid_dict:
            return uuid_dict.get(uuid)
        else:
            raise NoUserName(uuid)

    # ----------------------------------
    # do a POST to ``API_USERCATALOGS`` (or ``API_SERVICE_USERCATALOGS``)
    #   with {'displaynames': display_names}
    def _displayname_catalog(self, display_names, req_path):
        """Helper function to retrieve display names catalog"""
        req_headers = {'content-type': 'application/json'}
        req_body = parse_request({'displaynames': display_names}, self.logger)
        data = self._call_astakos(req_path, headers=req_headers,
                                  body=req_body, method="POST")
        if "displayname_catalog" in data:
            return data.get("displayname_catalog")
        else:
            msg = "_displayname_catalog request returned %s. " \
                  "No displayname_catalog found" % data
            self.logger.error(msg)
            raise AstakosClientException(msg)

    def get_uuids(self, display_names):
        """Return a displayname_catalog for the given names

        Keyword arguments:
        display_names   -- list of user names (list of strings)

        The returned displayname_catalog is a dictionary with
        the names as keys and the corresponding uuids as values

        """
        return self._displayname_catalog(
            display_names, self.api_usercatalogs)

    def get_uuid(self, display_name):
        """Return the uuid of a name (see getUUIDs)"""
        check_input("get_uuid", self.logger, display_name=display_name)
        name_dict = self.get_uuids([display_name])
        if display_name in name_dict:
            return name_dict.get(display_name)
        else:
            raise NoUUID(display_name)

    def service_get_uuids(self, display_names):
        """Return a display_name catalog using a service's token"""
        return self._displayname_catalog(
            display_names, self.api_service_usercatalogs)

    def service_get_uuid(self, display_name):
        """Return the uuid of a name using a service's token"""
        check_input("service_get_uuid", self.logger, display_name=display_name)
        name_dict = self.service_get_uuids([display_name])
        if display_name in name_dict:
            return name_dict.get(display_name)
        else:
            raise NoUUID(display_name)

    # ----------------------------------
    # do a GET to ``API_GETSERVICES``
    def get_services(self):
        """Return a list of dicts with the registered services"""
        return self._call_astakos(self.api_getservices)

    # ----------------------------------
    # do a GET to ``API_RESOURCES``
    def get_resources(self):
        """Return a dict of dicts with the available resources"""
        return self._call_astakos(self.api_resources)

    # ----------------------------------
    # do a POST to ``API_FEEDBACK``
    def send_feedback(self, message, data):
        """Send feedback to astakos service

        keyword arguments:
        message     -- Feedback message
        data        -- Additional information about service client status

        In case of success return nothing.
        Otherwise raise an AstakosClientException

        """
        check_input("send_feedback", self.logger, message=message, data=data)
        req_body = urllib.urlencode(
            {'feedback_msg': message, 'feedback_data': data})
        self._call_astakos(self.api_feedback, headers=None,
                           body=req_body, method="POST")

    # ----------------------------------
    # do a POST to ``API_TOKENS``
    def get_endpoints(self, tenant_name=None, non_authentication=False):
        """ Authenticate and get services' endpoints

        Keyword arguments:
        tenant_name         -- user's uniq id (optional)
        non_authentication  -- get only non authentication protected info


        It returns back the token as well as information about the token
        holder and the services he/she can acess (in json format).

        The tenant_name is optional and if it is given it must match the
        user's uuid.

        In case on of the `name', `type', `region', `version_id' parameters
        is given, return only the endpoints that match all of these criteria.
        If no match is found then raise NoEndpoints exception.

        In case of error raise an AstakosClientException.

        """
        req_headers = {'content-type': 'application/json'}
        if non_authentication:
            req_body = None
        else:
            body = {'auth': {'token': {'id': self.token}}}
            if tenant_name is not None:
                body['auth']['tenantName'] = tenant_name
            req_body = parse_request(body, self.logger)
        return self._call_astakos(self.api_tokens, headers=req_headers,
                                  body=req_body, method="POST",
                                  log_body=False)

    # ----------------------------------
    # do a GET to ``API_QUOTAS``
    def get_quotas(self):
        """Get user's quotas

        In case of success return a dict of dicts with user's current quotas.
        Otherwise raise an AstakosClientException

        """
        return self._call_astakos(self.api_quotas)

    # ----------------------------------
    # do a GET to ``API_SERVICE_QUOTAS``
    def service_get_quotas(self, user=None):
        """Get all quotas for resources associated with the service

        Keyword arguments:
        user    -- optionally, the uuid of a specific user

        In case of success return a dict of dicts of dicts with current quotas
        for all users, or of a specified user, if user argument is set.
        Otherwise raise an AstakosClientException

        """
        query = self.api_service_quotas
        if user is not None:
            query += "?user=" + user
        return self._call_astakos(query)

    # ----------------------------------
    # do a POST to ``API_COMMISSIONS``
    def issue_commission(self, request):
        """Issue a commission

        Keyword arguments:
        request -- commision request (dict)

        In case of success return commission's id (int).
        Otherwise raise an AstakosClientException.

        """
        req_headers = {'content-type': 'application/json'}
        req_body = parse_request(request, self.logger)
        try:
            response = self._call_astakos(self.api_commissions,
                                          headers=req_headers,
                                          body=req_body,
                                          method="POST")
        except AstakosClientException as err:
            if err.status == 413:
                raise QuotaLimit(err.message, err.details)
            else:
                raise

        if "serial" in response:
            return response['serial']
        else:
            msg = "issue_commission_core request returned %s. " + \
                  "No serial found" % response
            self.logger.error(msg)
            raise AstakosClientException(msg)

    def issue_one_commission(self, holder, source, provisions,
                             name="", force=False, auto_accept=False):
        """Issue one commission (with specific holder and source)

        keyword arguments:
        holder      -- user's id (string)
        source      -- commission's source (ex system) (string)
        provisions  -- resources with their quantity (dict from string to int)
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
                prov = {"holder": holder, "source": source,
                        "resource": resource, "quantity": quantity}
                request["provisions"].append(prov)
        except Exception as err:
            self.logger.error(str(err))
            raise BadValue(str(err))

        return self.issue_commission(request)

    # ----------------------------------
    # do a GET to ``API_COMMISSIONS``
    def get_pending_commissions(self):
        """Get Pending Commissions

        In case of success return a list of pending commissions' ids
        (list of integers)

        """
        return self._call_astakos(self.api_commissions)

    # ----------------------------------
    # do a GET to ``API_COMMISSIONS``/<serial>
    def get_commission_info(self, serial):
        """Get Description of a Commission

        Keyword arguments:
        serial  -- commission's id (int)

        In case of success return a dict of dicts containing
        informations (details) about the requested commission

        """
        check_input("get_commission_info", self.logger, serial=serial)

        path = self.api_commissions.rstrip('/') + "/" + str(serial)
        return self._call_astakos(path)

    # ----------------------------------
    # do a POST to ``API_COMMISSIONS``/<serial>/action"
    def commission_action(self, serial, action):
        """Perform a commission action

        Keyword arguments:
        serial  -- commission's id (int)
        action  -- action to perform, currently accept/reject (string)

        In case of success return nothing.

        """
        check_input("commission_action", self.logger,
                    serial=serial, action=action)

        path = self.api_commissions.rstrip('/') + "/" + str(serial) + "/action"
        req_headers = {'content-type': 'application/json'}
        req_body = parse_request({str(action): ""}, self.logger)
        self._call_astakos(path, headers=req_headers,
                           body=req_body, method="POST")

    def accept_commission(self, serial):
        """Accept a commission (see commission_action)"""
        self.commission_action(serial, "accept")

    def reject_commission(self, serial):
        """Reject a commission (see commission_action)"""
        self.commission_action(serial, "reject")

    # ----------------------------------
    # do a POST to ``API_COMMISSIONS_ACTION``
    def resolve_commissions(self, accept_serials, reject_serials):
        """Resolve multiple commissions at once

        Keyword arguments:
        accept_serials  -- commissions to accept (list of ints)
        reject_serials  -- commissions to reject (list of ints)

        In case of success return a dict of dicts describing which
        commissions accepted, which rejected and which failed to
        resolved.

        """
        check_input("resolve_commissions", self.logger,
                    accept_serials=accept_serials,
                    reject_serials=reject_serials)

        req_headers = {'content-type': 'application/json'}
        req_body = parse_request({"accept": accept_serials,
                                  "reject": reject_serials},
                                 self.logger)
        return self._call_astakos(self.api_commissions_action,
                                  headers=req_headers, body=req_body,
                                  method="POST")

    # ----------------------------
    # do a GET to ``API_PROJECTS``
    def get_projects(self, name=None, state=None, owner=None):
        """Retrieve all accessible projects

        Arguments:
        name  -- filter by name (optional)
        state -- filter by state (optional)
        owner -- filter by owner (optional)

        In case of success, return a list of project descriptions.
        """
        filters = {}
        if name is not None:
            filters["name"] = name
        if state is not None:
            filters["state"] = state
        if owner is not None:
            filters["owner"] = owner
        req_headers = {'content-type': 'application/json'}
        req_body = (parse_request({"filter": filters}, self.logger)
                    if filters else None)
        return self._call_astakos(self.api_projects,
                                  headers=req_headers, body=req_body)

    # -----------------------------------------
    # do a GET to ``API_PROJECTS``/<project_id>
    def get_project(self, project_id):
        """Retrieve project description, if accessible

        Arguments:
        project_id -- project identifier

        In case of success, return project description.
        """
        path = join_urls(self.api_projects, str(project_id))
        return self._call_astakos(path)

    # -----------------------------
    # do a POST to ``API_PROJECTS``
    def create_project(self, specs):
        """Submit application to create a new project

        Arguments:
        specs -- dict describing a project

        In case of success, return project and application identifiers.
        """
        req_headers = {'content-type': 'application/json'}
        req_body = parse_request(specs, self.logger)
        return self._call_astakos(self.api_projects,
                                  headers=req_headers, body=req_body,
                                  method="POST")

    # ------------------------------------------
    # do a POST to ``API_PROJECTS``/<project_id>
    def modify_project(self, project_id, specs):
        """Submit application to modify an existing project

        Arguments:
        project_id -- project identifier
        specs      -- dict describing a project

        In case of success, return project and application identifiers.
        """
        path = join_urls(self.api_projects, str(project_id))
        req_headers = {'content-type': 'application/json'}
        req_body = parse_request(specs, self.logger)
        return self._call_astakos(path, headers=req_headers,
                                  body=req_body, method="POST")

    # -------------------------------------------------
    # do a POST to ``API_PROJECTS``/<project_id>/action
    def project_action(self, project_id, action, reason=""):
        """Perform action on a project

        Arguments:
        project_id -- project identifier
        action     -- action to perform, one of "suspend", "unsuspend",
                      "terminate", "reinstate"
        reason     -- reason of performing the action

        In case of success, return nothing.
        """
        path = join_urls(self.api_projects, str(project_id))
        path = join_urls(path, "action")
        req_headers = {'content-type': 'application/json'}
        req_body = parse_request({action: reason}, self.logger)
        return self._call_astakos(path, headers=req_headers,
                                  body=req_body, method="POST")

    # --------------------------------
    # do a GET to ``API_APPLICATIONS``
    def get_applications(self, project=None):
        """Retrieve all accessible applications

        Arguments:
        project -- filter by project (optional)

        In case of success, return a list of application descriptions.
        """
        req_headers = {'content-type': 'application/json'}
        body = {"project": project} if project is not None else None
        req_body = parse_request(body, self.logger) if body else None
        return self._call_astakos(self.api_applications,
                                  headers=req_headers, body=req_body)

    # -----------------------------------------
    # do a GET to ``API_APPLICATIONS``/<app_id>
    def get_application(self, app_id):
        """Retrieve application description, if accessible

        Arguments:
        app_id -- application identifier

        In case of success, return application description.
        """
        path = join_urls(self.api_applications, str(app_id))
        return self._call_astakos(path)

    # -------------------------------------------------
    # do a POST to ``API_APPLICATIONS``/<app_id>/action
    def application_action(self, app_id, action, reason=""):
        """Perform action on an application

        Arguments:
        app_id -- application identifier
        action -- action to perform, one of "approve", "deny",
                  "dismiss", "cancel"
        reason -- reason of performing the action

        In case of success, return nothing.
        """
        path = join_urls(self.api_applications, str(app_id))
        path = join_urls(path, "action")
        req_headers = {'content-type': 'application/json'}
        req_body = parse_request({action: reason}, self.logger)
        return self._call_astakos(path, headers=req_headers,
                                  body=req_body, method="POST")

    # -------------------------------
    # do a GET to ``API_MEMBERSHIPS``
    def get_memberships(self, project=None):
        """Retrieve all accessible memberships

        Arguments:
        project -- filter by project (optional)

        In case of success, return a list of membership descriptions.
        """
        req_headers = {'content-type': 'application/json'}
        body = {"project": project} if project is not None else None
        req_body = parse_request(body, self.logger) if body else None
        return self._call_astakos(self.api_memberships,
                                  headers=req_headers, body=req_body)

    # -----------------------------------------
    # do a GET to ``API_MEMBERSHIPS``/<memb_id>
    def get_membership(self, memb_id):
        """Retrieve membership description, if accessible

        Arguments:
        memb_id -- membership identifier

        In case of success, return membership description.
        """
        path = join_urls(self.api_memberships, str(memb_id))
        return self._call_astakos(path)

    # -------------------------------------------------
    # do a POST to ``API_MEMBERSHIPS``/<memb_id>/action
    def membership_action(self, memb_id, action, reason=""):
        """Perform action on a membership

        Arguments:
        memb_id -- membership identifier
        action  -- action to perform, one of "leave", "cancel", "accept",
                   "reject", "remove"
        reason  -- reason of performing the action

        In case of success, return nothing.
        """
        path = join_urls(self.api_memberships, str(memb_id))
        path = join_urls(path, "action")
        req_headers = {'content-type': 'application/json'}
        req_body = parse_request({action: reason}, self.logger)
        return self._call_astakos(path, headers=req_headers,
                                  body=req_body, method="POST")

    # --------------------------------
    # do a POST to ``API_MEMBERSHIPS``
    def join_project(self, project_id):
        """Join a project

        Arguments:
        project_id -- project identifier

        In case of success, return membership identifier.
        """
        req_headers = {'content-type': 'application/json'}
        body = {"join": {"project": project_id}}
        req_body = parse_request(body, self.logger)
        return self._call_astakos(self.api_memberships, headers=req_headers,
                                  body=req_body, method="POST")

    # --------------------------------
    # do a POST to ``API_MEMBERSHIPS``
    def enroll_member(self, project_id, email):
        """Enroll a user in a project

        Arguments:
        project_id -- project identifier
        email      -- user identified by email

        In case of success, return membership identifier.
        """
        req_headers = {'content-type': 'application/json'}
        body = {"enroll": {"project": project_id, "user": email}}
        req_body = parse_request(body, self.logger)
        return self._call_astakos(self.api_memberships, headers=req_headers,
                                  body=req_body, method="POST")


# --------------------------------------------------------------------
# parse endpoints
def parse_endpoints(endpoints, ep_name=None, ep_type=None,
                    ep_region=None, ep_version_id=None):
    """Parse endpoints server response and extract the ones needed

    Keyword arguments:
    endpoints     -- the endpoints (json response from get_endpoints)
    ep_name       -- return only endpoints with this name (optional)
    ep_type       -- return only endpoints with this type (optional)
    ep_region     -- return only endpoints with this region (optional)
    ep_version_id -- return only endpoints with this versionId (optional)

    In case on of the `name', `type', `region', `version_id' parameters
    is given, return only the endpoints that match all of these criteria.
    If no match is found then raise NoEndpoints exception.

    """
    try:
        catalog = endpoints['access']['serviceCatalog']
        if ep_name is not None:
            catalog = \
                [c for c in catalog if c['name'] == ep_name]
        if ep_type is not None:
            catalog = \
                [c for c in catalog if c['type'] == ep_type]
        if ep_region is not None:
            for c in catalog:
                c['endpoints'] = [e for e in c['endpoints']
                                  if e['region'] == ep_region]
            # Remove catalog entries with no endpoints
            catalog = \
                [c for c in catalog if c['endpoints']]
        if ep_version_id is not None:
            for c in catalog:
                c['endpoints'] = [e for e in c['endpoints']
                                  if e['versionId'] == ep_version_id]
            # Remove catalog entries with no endpoints
            catalog = \
                [c for c in catalog if c['endpoints']]

        if not catalog:
            raise NoEndpoints(ep_name, ep_type,
                              ep_region, ep_version_id)
        else:
            return catalog
    except KeyError:
        raise NoEndpoints()


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
