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
Simple and minimal client for the Astakos authentication service
"""

import logging
import urlparse
import urllib
import hashlib
from base64 import b64encode
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
            logger = logging.getLogger("astakosclient")
            logger.setLevel(logging.INFO)
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

    def _fill_endpoints(self, endpoints, extra=False):
        """Fill the endpoints for our AstakosClient

        This will be done once (lazily) and the endpoints will be there
        to be used afterwards.
        The `extra' parameter is there for compatibility reasons. We are going
        to fill the oauth2 endpoint only if we need it. This way we are keeping
        astakosclient compatible with older Astakos version.

        """
        astakos_service_catalog = parse_endpoints(
            endpoints, ep_name="astakos_account", ep_version_id="v1.0")
        self._account_url = \
            astakos_service_catalog[0]['endpoints'][0]['publicURL']
        parsed_account_url = urlparse.urlparse(self._account_url)

        self._account_prefix = parsed_account_url.path
        self.logger.debug("Got account_prefix \"%s\"" % self._account_prefix)

        self._ui_url = \
            astakos_service_catalog[0]['endpoints'][0]['SNF:uiURL']
        parsed_ui_url = urlparse.urlparse(self._ui_url)

        self._ui_prefix = parsed_ui_url.path
        self.logger.debug("Got ui_prefix \"%s\"" % self._ui_prefix)

        if extra:
            oauth2_service_catalog = \
                parse_endpoints(endpoints, ep_name="astakos_oauth2")
            self._oauth2_url = \
                oauth2_service_catalog[0]['endpoints'][0]['publicURL']
            parsed_oauth2_url = urlparse.urlparse(self._oauth2_url)
            self._oauth2_prefix = parsed_oauth2_url.path

    def _get_value(self, s, extra=False):
        assert s in ['_account_url', '_account_prefix',
                     '_ui_url', '_ui_prefix',
                     '_oauth2_url', '_oauth2_prefix']
        try:
            return getattr(self, s)
        except AttributeError:
            self.get_endpoints(extra=extra)
            return getattr(self, s)

    @property
    def account_url(self):
        return self._get_value('_account_url')

    @property
    def account_prefix(self):
        return self._get_value('_account_prefix')

    @property
    def ui_url(self):
        return self._get_value('_ui_url')

    @property
    def ui_prefix(self):
        return self._get_value('_ui_prefix')

    @property
    def oauth2_url(self):
        return self._get_value('_oauth2_url', extra=True)

    @property
    def oauth2_prefix(self):
        return self._get_value('_oauth2_prefix', extra=True)

    @property
    def api_usercatalogs(self):
        return join_urls(self.account_prefix, "user_catalogs")

    @property
    def api_service_usercatalogs(self):
        return join_urls(self.account_prefix, "service/user_catalogs")

    @property
    def api_resources(self):
        return join_urls(self.account_prefix, "resources")

    @property
    def api_quotas(self):
        return join_urls(self.account_prefix, "quotas")

    @property
    def api_service_quotas(self):
        return join_urls(self.account_prefix, "service_quotas")

    @property
    def api_service_project_quotas(self):
        return join_urls(self.account_prefix, "service_project_quotas")

    @property
    def api_commissions(self):
        return join_urls(self.account_prefix, "commissions")

    @property
    def api_commissions_action(self):
        return join_urls(self.api_commissions, "action")

    @property
    def api_feedback(self):
        return join_urls(self.account_prefix, "feedback")

    @property
    def api_projects(self):
        return join_urls(self.account_prefix, "projects")

    @property
    def api_memberships(self):
        return join_urls(self.api_projects, "memberships")

    @property
    def api_getservices(self):
        return join_urls(self.ui_prefix, "get_services")

    @property
    def api_oauth2_auth(self):
        return join_urls(self.oauth2_prefix, "auth")

    @property
    def api_oauth2_token(self):
        return join_urls(self.oauth2_prefix, "token")

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
        # Initialize log_request and log_response attributes
        self.log_request = None
        self.log_response = None

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
                # Log the request so other clients (like kamaki)
                # can use them to produce their own log messages.
                self.log_request = dict(method=method, path=request_path)
                self.log_request.update(kwargs)

                # Send request
                # Used * or ** magic. pylint: disable-msg=W0142
                (message, data, status) = \
                    _do_request(conn, method, request_path, **kwargs)

                # Log the response so other clients (like kamaki)
                # can use them to produce their own log messages.
                self.log_response = dict(
                    status=status, message=message, data=data)
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

    # -----------------------------------------
    # do a POST to ``API_TOKENS`` with no token
    def get_endpoints(self, extra=False):
        """ Get services' endpoints

        The extra parameter is to be used by _fill_endpoints.
        In case of error raise an AstakosClientException.

        """
        req_headers = {'content-type': 'application/json'}
        req_body = None
        r = self._call_astakos(self.api_tokens, headers=req_headers,
                               body=req_body, method="POST",
                               log_body=False)
        self._fill_endpoints(r, extra=extra)
        return r

    # --------------------------------------
    # do a POST to ``API_TOKENS`` with a token
    def authenticate(self, tenant_name=None):
        """ Authenticate and get services' endpoints

        Keyword arguments:
        tenant_name         -- user's uniq id (optional)

        It returns back the token as well as information about the token
        holder and the services he/she can access (in json format).

        The tenant_name is optional and if it is given it must match the
        user's uuid.

        In case of error raise an AstakosClientException.

        """
        req_headers = {'content-type': 'application/json'}
        body = {'auth': {'token': {'id': self.token}}}
        if tenant_name is not None:
            body['auth']['tenantName'] = tenant_name
        req_body = parse_request(body, self.logger)
        r = self._call_astakos(self.api_tokens, headers=req_headers,
                               body=req_body, method="POST",
                               log_body=False)
        self._fill_endpoints(r)
        return r

    # --------------------------------------
    # do a GET to ``API_TOKENS`` with a token
    def validate_token(self, token_id, belongs_to=None):
        """ Validate a temporary access token (oath2)

        Keyword arguments:
        belongsTo         -- confirm that token belongs to tenant

        It returns back the token as well as information about the token
        holder.

        The belongs_to is optional and if it is given it must be inside the
        token's scope.

        In case of error raise an AstakosClientException.

        """
        path = join_urls(self.api_tokens, str(token_id))
        if belongs_to is not None:
            params = {'belongsTo': belongs_to}
            path = '%s?%s' % (path, urllib.urlencode(params))
        return self._call_astakos(path, method="GET", log_body=False)

    # ----------------------------------
    # do a GET to ``API_QUOTAS``
    def get_quotas(self):
        """Get user's quotas

        In case of success return a dict of dicts with user's current quotas.
        Otherwise raise an AstakosClientException

        """
        return self._call_astakos(self.api_quotas)

    def _join_if_list(self, val):
        return ','.join(map(str, val)) if isinstance(val, list) else val

    # ----------------------------------
    # do a GET to ``API_SERVICE_QUOTAS``
    def service_get_quotas(self, user=None, project=None):
        """Get all quotas for resources associated with the service

        Keyword arguments:
        user    -- optionally, the uuid of a specific user, or a list thereof
        project -- optionally, the uuid of a specific project, or a list
                   thereof

        In case of success return a dict of dicts of dicts with current quotas
        for all users, or of a specified user, if user argument is set.
        Otherwise raise an AstakosClientException

        """
        query = self.api_service_quotas
        filters = {}
        if user is not None:
            filters['user'] = self._join_if_list(user)
        if project is not None:
            filters['project'] = self._join_if_list(project)
        if filters:
            query += "?" + urllib.urlencode(filters)
        return self._call_astakos(query)

    # ----------------------------------
    # do a GET to ``API_SERVICE_PROJECT_QUOTAS``
    def service_get_project_quotas(self, project=None):
        """Get all project quotas for resources associated with the service

        Keyword arguments:
        project    -- optionally, the uuid of a specific project, or a list
                      thereof

        In case of success return a dict of dicts with current quotas
        for all projects, or of a specified project, if project argument is
        set. Otherwise raise an AstakosClientException

        """
        query = self.api_service_project_quotas
        filters = {}
        if project is not None:
            filters['project'] = self._join_if_list(project)
        if filters:
            query += "?" + urllib.urlencode(filters)
        return self._call_astakos(query)

    # ----------------------------------
    # do a POST to ``API_COMMISSIONS``
    def _issue_commission(self, request):
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

    def _mk_user_provision(self, holder, source, resource, quantity):
        holder = "user:" + holder
        source = "project:" + source
        return {"holder": holder, "source": source,
                "resource": resource, "quantity": quantity}

    def _mk_project_provision(self, holder, resource, quantity):
        holder = "project:" + holder
        return {"holder": holder, "source": None,
                "resource": resource, "quantity": quantity}

    def mk_provisions(self, holder, source, resource, quantity):
        return [self._mk_user_provision(holder, source, resource, quantity),
                self._mk_project_provision(source, resource, quantity)]

    def issue_commission_generic(self, user_provisions, project_provisions,
                                 name="", force=False, auto_accept=False):
        """Issue commission (for multiple holder/source pairs)

        keyword arguments:
        user_provisions  -- dict mapping user holdings
                            (user, project, resource) to integer quantities
        project_provisions -- dict mapping project holdings
                              (project, resource) to integer quantities
        name        -- description of the commission (string)
        force       -- force this commission (boolean)
        auto_accept -- auto accept this commission (boolean)

        In case of success return commission's id (int).
        Otherwise raise an AstakosClientException.

        """
        request = {}
        request["force"] = force
        request["auto_accept"] = auto_accept
        request["name"] = name
        try:
            request["provisions"] = []
            for (holder, source, resource), quantity in \
                    user_provisions.iteritems():
                p = self._mk_user_provision(holder, source, resource, quantity)
                request["provisions"].append(p)
            for (holder, resource), quantity in project_provisions.iteritems():
                p = self._mk_project_provision(holder, resource, quantity)
                request["provisions"].append(p)
        except Exception as err:
            self.logger.error(str(err))
            raise BadValue(str(err))

        return self._issue_commission(request)

    def issue_one_commission(self, holder, provisions,
                             name="", force=False, auto_accept=False):
        """Issue one commission (with specific holder and source)

        keyword arguments:
        holder      -- user's id (string)
        provisions  -- (source, resource) mapping to quantity
        name        -- description of the commission (string)
        force       -- force this commission (boolean)
        auto_accept -- auto accept this commission (boolean)

        In case of success return commission's id (int).
        Otherwise raise an AstakosClientException.

        """
        check_input("issue_one_commission", self.logger,
                    holder=holder, provisions=provisions)

        request = {}
        request["force"] = force
        request["auto_accept"] = auto_accept
        request["name"] = name
        try:
            request["provisions"] = []
            for (source, resource), quantity in provisions.iteritems():
                ps = self.mk_provisions(holder, source, resource, quantity)
                request["provisions"].extend(ps)
        except Exception as err:
            self.logger.error(str(err))
            raise BadValue(str(err))

        return self._issue_commission(request)

    def issue_resource_reassignment(self, holder, provisions, name="",
                                    force=False, auto_accept=False):
        """Change resource assignment to another project
        """

        request = {}
        request["force"] = force
        request["auto_accept"] = auto_accept
        request["name"] = name

        try:
            request["provisions"] = []
            for key, quantity in provisions.iteritems():
                (from_source, to_source, resource) = key
                ps = self.mk_provisions(
                    holder, from_source, resource, -quantity)
                ps += self.mk_provisions(holder, to_source, resource, quantity)
                request["provisions"].extend(ps)
        except Exception as err:
            self.logger.error(str(err))
            raise BadValue(str(err))

        return self._issue_commission(request)

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
    def get_projects(self, name=None, state=None, owner=None, mode=None):
        """Retrieve all accessible projects

        Arguments:
        name  -- filter by name (optional)
        state -- filter by state (optional)
        owner -- filter by owner (optional)
        mode  -- if value is 'member', return only active projects in which
                 the request user is an active member

        In case of success, return a list of project descriptions.
        """
        filters = {}
        if name is not None:
            filters["name"] = name
        if state is not None:
            filters["state"] = state
        if owner is not None:
            filters["owner"] = owner
        if mode is not None:
            filters["mode"] = mode
        path = self.api_projects
        if filters:
            path += "?" + urllib.urlencode(filters)
        req_headers = {'content-type': 'application/json'}
        return self._call_astakos(path, headers=req_headers)

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
    # do a PUT to ``API_PROJECTS``/<project_id>
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
                                  body=req_body, method="PUT")

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
        req_body = parse_request({action: {"reason": reason}}, self.logger)
        return self._call_astakos(path, headers=req_headers,
                                  body=req_body, method="POST")

    # -------------------------------------------------
    # do a POST to ``API_PROJECTS``/<project_id>/action
    def application_action(self, project_id, app_id, action, reason=""):
        """Perform action on a project application

        Arguments:
        project_id -- project identifier
        app_id     -- application identifier
        action     -- action to perform, one of "approve", "deny",
                      "dismiss", "cancel"
        reason     -- reason of performing the action

        In case of success, return nothing.
        """
        path = join_urls(self.api_projects, str(project_id))
        path = join_urls(path, "action")
        req_headers = {'content-type': 'application/json'}
        req_body = parse_request({action: {
            "reasons": reason,
            "app_id": app_id}}, self.logger)
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
        filters = {}
        if project is not None:
            filters["project"] = project
        path = self.api_memberships
        if filters:
            path += '?' + urllib.urlencode(filters)
        return self._call_astakos(path, headers=req_headers)

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

    # --------------------------------
    # do a POST to ``API_OAUTH2_TOKEN``
    def get_token(self, grant_type, client_id, client_secret, **body_params):
        headers = {'content-type': 'application/x-www-form-urlencoded',
                   'Authorization': 'Basic %s' % b64encode('%s:%s' %
                                                           (client_id,
                                                            client_secret))}
        body_params['grant_type'] = grant_type
        body = urllib.urlencode(body_params)
        return self._call_astakos(self.api_oauth2_token, headers=headers,
                                  body=body, method="POST")


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

    In case one of the `name', `type', `region', `version_id' parameters
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
        raise NoEndpoints(ep_name, ep_type, ep_region, ep_version_id)


# --------------------------------------------------------------------
# Private functions
# We want _do_request to be a distinct function
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
