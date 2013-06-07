.. _astakosclient:

Component astakosclient
^^^^^^^^^^^^^^^^^^^^^^^

The Synnefo component :ref:`astakosclient <astakosclient>` defines a
default client for the :ref:`Astakos <astakos>` service. It is designed to be
simple and minimal, hence easy to debug and test.

It uses the user's authentication token to query Astakos for:

    * User's info
    * Usernames for given UUIDs
    * UUIDs for given usernames
    * User's quotas

It can also query Astakos with another service's (Cyclades or Pithos)
authentication token for:

    * Usernames for given UUIDs
    * UUIDs for given usernames
    * Quotas for all related resources
    * Issue commissions
    * Get pending commissions
    * Accept or reject commissions

Additionally, there are options for using the `objpool
<https://github.com/grnet/objpool>`_ library to pool the http connections.


Basic example
=============

The ``astakosclient`` module provides the ``AstakosClient`` class. This section
demonstrates how to get user's info using ``astakosclient``.

.. code-block:: python

    from astakosclient import AstakosClient

    client = AstakosClient("https://accounts.example.com")
    user_info = client.get_user_info("UQpYas7ElzWGD5yCcEXtjw")
    print user_info['username']

Another example where we ask for the username of a user with UUID:
``b3de8eb0-3958-477e-als9-789af8dd352c``

.. code-block:: python

    from astakosclient import AstakosClient

    client = AstakosClient("https://accounts.example.com")
    username = client.get_username("UQpYas7ElzWGD5yCcEXtjw",
                                   "b3de8eb0-3958-477e-als9-789af8dd352c")
    print username


Classes and functions
=====================

This section describes in depth the API of ``astakosclient``.

Astakos Client
--------------

*class* astakosclient.\ **AstakosClient(**\ astakos_url,
retry=0, use_pool=False, pool_size=8, logger=None\ **)**

    Initialize an instance of **AstakosClient** given the *astakos_url*.
    Optionally one can specify if we are going to use a pool, the pool_size
    and the number of retries if the connection fails.

    This class provides the following methods:

    **get_user_info(**\ token, usage=False\ **)**
        Given a user's authentication token it returns a dict with the
        correspoinding user's info. If usage is set to True more
        information about user's resources will be returned.
        In case of error raise an AstakosClientException exception.

    **get_usernames(**\ token, uuids\ **)**
        Given a user's authentication token and a list of UUIDs
        return a uuid_catalog, that is a dictionary with the given
        UUIDs as keys and the corresponding user names as values.
        Invalid UUIDs will not be in the dictionary.
        In case of error raise an AstakosClientException exception.

    **get_username(**\ token, uuid\ **)**
        Given a user's authentication token and a UUID (as string)
        return the corresponding user name (as string).
        In case of invalid UUID raise NoUserName exception.
        In case of error raise an AstakosClientException exception.

    **service_get_usernames(**\ token, uuids\ **)**
        Same as get_usernames but called with a service's token.

    **service_get_username(**\ token, uuid\ **)**
        Same as get_username but called with a service's token.

    **get_uuids(**\ token, display_names\ **)**
        Given a user's authentication token and a list of usernames
        return a displayname_catalog, that is a dictionary with the given
        usernames as keys and the corresponding UUIDs as values.
        Invalid usernames will not be in the dictionary.
        In case of error raise an AstakosClientException exception.

    **get_uuid(**\ token, display_name\ **)**
        Given a user's authentication token and a username (as string)
        return the corresponding UUID (as string).
        In case of invalid user name raise NoUUID exception.
        In case of error raise an AstakosClientException exception.

    **service_get_uuids(**\ token, uuids\ **)**
        Same as get_uuids but called with a service's token.

    **service_get_uuid(**\ token, uuid\ **)**
        Same as get_uuid but called with a service's token.

    **get_services()**
        Return a list of dicts with the registered services.

    **get_resources()**
        Return a list of dicts with the available resources

    **send_feedback(**\ token, message, data\ **)**
        Using a user's authentication token send some feedback to
        astakos service. Additional information about the service
        client status can be given in the data variable.
        In case of success returns nothing.
        Otherwise raise an AstakosClientException exception.

    **get_endpoints(**\ token, belongs_to, marker, limit\ **)**
        Given a user's authentication token, request registered
        endpoints from astakos service. If belongs_to is given (uuid)
        check that the token belongs to this user. If marker is given
        (int) return endpoints (ordered by ID) whose ID is higher than
        the marker. Limit (int) specifies the maximum number of
        endpoints to return. Return a json formatted dictionary containing
        information about registered endpoints.

        .. warning:: *get_endpoints* api call encodes the user's token inside
            the url. It's security unsafe to use it (both astakosclient
            and nginx tend to log requested urls). Use
            get_user_info_with_endpoints instead.

    **get_user_info_with_endpoints(**\ token, uuid=None\ **)**
        Fallback call which receives the user token or the user uuid/token
        and returns back the token as well as information about the token
        holder and the services he/seh can access.
        In case of error raise an AstakosClientException exception.

    **get_quotas(**\ token\ **)**
        Given a user's authentication token return user's
        current quotas (as dict of dicts).
        In case of error raise an AstakosClientException exception.

    **service_get_quotas(**\ token, user=None\ **)**
        Given a service's authentication token return all users'
        current quotas for the resources associated with the service
        (as dict of dicts of dicts).
        Optionally, one can query the quotas of a specific user with
        argument user=UUID.
        In case of error raise an AstakosClientException exception.

    **issue_commission(**\ token, request\ **)**
        Given a service's authentication token issue a commission.
        In case of success return commission's id (int).
        Otherwise raise an AstakosClientException exception.

    **issue_one_commission(**\ token, holder, source, provisions, name="", force=False, auto_accept=False\ **)**
        Given a service's authentication token issue a commission.
        In this case we specify the holder, the source and the provisions
        (a dict from string to int) and astakosclient will create the
        corresponding commission.
        In case of success return commission's id (int).
        Otherwise raise an AstakosClientException exception.

    **get_pending_commissions(**\ token\ **)**
        Given a service's authentication token return the pending
        commissions (list of integers).
        In case of error raise an AstakosClientException exception.

    **get_commission_info(**\ token, serial\ **)**
        Given a service's authentication token and the id of a
        pending commission return a dict of dicts containting
        informations (details) about the requested commission.
        In case of error raise an AstakosClientException exception.

    **commission_action(**\ token, serial, action\ **)**
        Given a service's authentication token and the id of a
        pending commission, request the specified action (currently
        one of accept, reject).
        In case of success returns nothing.
        Otherwise raise an AstakosClientException exception.

    **accept_commission(**\ token, serial\ **)**
        Accept a pending commission (see commission_action).

    **reject_commission(**\ token, serial\ **)**
        Reject a pending commission (see commission_action).

    **resolve_commissions(**\ token, accept_serials, reject_serials\ **)**
        Accept or Reject many pending commissions at once.
        In case of success return a dict of dicts describing which
        commissions accepted, which rejected and which failed to
        resolved.
        Otherwise raise an AstakosClientException exception.


Public Functions
----------------

**get_token_from_cookie(**\ request, cookie_name\ **)**
    Given a Django request object and an Astakos cookie name
    extract the user's token from it.


Exceptions and Errors
=====================

*exception* **AstakosClientException**
    Raised in case of an error. It contains an error message and the
    corresponding http status code. Other exceptions raised by
    astakosclient module are derived from this one.

*exception* **BadValue**
    A redefinition of ValueError exception under AstakosClientException.

*exception* **InvalidResponse**
    This exception is raised whenever the server's response is not
    valid json (cannot be parsed by simplejson library).

*exception* **BadRequest**
    Raised in case of a Bad Request, with status 400.

*exception* **Unauthorized**
    Raised in case of Invalid token (unauthorized access), with status 401.

*exception* **Forbidden**
    The server understood the request, but is refusing to fulfill it.
    Status 401.

*exception* **NotFound**
    The server has not found anything matching the Request-URI. Status 404.

*exception* **QuotaLimit**
    Quantity fell below zero or exceeded capacity in one of the holdings.

*exception* **NoUserName**
    Raised by getDisplayName and getServiceDisplayName when an invalid
    UUID was given.

*exception* **NoUUID**
    Raised by *getUUID* and *getServiceUUID* when an invalid
    username was given.
