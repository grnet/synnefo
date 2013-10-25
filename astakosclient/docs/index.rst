.. _astakosclient:

Component astakosclient
^^^^^^^^^^^^^^^^^^^^^^^

The Synnefo component astakosclient_ defines a
default client for the `Astakos <astakos>`_ service. It is designed to be
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

    client = AstakosClient("UQpYas7ElzWGD5yCcEXtjw",
                           "https://accounts.example.com")
    user_info = client.get_user_info()
    print user_info['username']

Another example where we ask for the username of a user with UUID:
``b3de8eb0-3958-477e-als9-789af8dd352c``

.. code-block:: python

    from astakosclient import AstakosClient

    client = AstakosClient("UQpYas7ElzWGD5yCcEXtjw",
                           "https://accounts.example.com")
    username = client.get_username("b3de8eb0-3958-477e-als9-789af8dd352c")
    print username


Classes and functions
=====================

This section describes in depth the API of ``astakosclient``.

Astakos Client
--------------

*class* astakosclient.\ **AstakosClient(**\ token, auth_url,
retry=0, use_pool=False, pool_size=8, logger=None\ **)**

    Initialize an instance of **AstakosClient** given the Authentication Url
    *auth_url* and the Token *token*.
    Optionally one can specify if we are going to use a pool, the pool_size
    and the number of retries if the connection fails.

    This class provides the following methods:

    **authenticate(**\ tenant_name=None\ **)**
        It authenticates the user and returns information about the user,
        their token as well as the service endpoints one can access. In
        case of error, it raises an AstakosClientException exception.

    **get_user_info()**
        It returns a dict with the corresponding user's info. In case of
        error, it raises an AstakosClientException exception.

    **get_usernames(**\ uuids\ **)**
        Given a list of UUIDs it returns a uuid_catalog, that is a dictionary
        with the given UUIDs as keys and the corresponding user names as
        values.  Invalid UUIDs will not be in the dictionary.  In case of
        error, it raises an AstakosClientException exception.

    **get_username(**\ uuid\ **)**
        Given a UUID (as string) it returns the corresponding user name (as
        string).  In case of invalid UUID it raises NoUserName exception.  In
        case of error, it raises an AstakosClientException exception.

    **service_get_usernames(**\ uuids\ **)**
        Same as get_usernames but used with service tokens.

    **service_get_username(**\ uuid\ **)**
        Same as get_username but used with service tokens.

    **get_uuids(**\ display_names\ **)**
        Given a list of usernames it returns a displayname_catalog, that is a
        dictionary with the given usernames as keys and the corresponding UUIDs
        as values.  Invalid usernames will not be in the dictionary.  In case
        of error, it raises an AstakosClientException exception.

    **get_uuid(**\ display_name\ **)**
        Given a username (as string) it returns the corresponding UUID (as
        string).  In case of invalid user name it raises NoUUID exception.  In
        case of error, it raises an AstakosClientException exception.

    **service_get_uuids(**\ uuids\ **)**
        Same as get_uuids but used with service tokens.

    **service_get_uuid(**\ uuid\ **)**
        Same as get_uuid but used with service tokens.

    **get_services()**
        Return a list of dicts with the registered services.

    **get_resources()**
        Return a list of dicts with the available resources

    **send_feedback(**\ message, data\ **)**
        Send some feedback to astakos service. Additional information about the
        service client status can be given in the data variable.  In case of
        success it returns nothing.  Otherwise it raises an
        AstakosClientException exception.

    **get_endpoints()**
        It returns the services URLs one can access. In case of error it
        raises an AstakosClientException exception.

    **get_quotas()**
        It returns user's current quotas (as dict of dicts). In case of error
        it raises an AstakosClientException exception.

    **service_get_quotas(**\ user=None\ **)**
        It returns all users' current quotas for the resources associated with
        the service (as dict of dicts of dicts). Optionally, one can query the
        quotas of a specific user with argument user=UUID. In case of error it
        raises an AstakosClientException exception.

    **issue_commission(**\ request\ **)**
        Issue a commission. In case of success it returns commission's id
        (int). Otherwise it raises an AstakosClientException exception.

    **issue_one_commission(**\ holder, source, provisions, name="", force=False, auto_accept=False\ **)**
        Issue a commission. We have to specify the holder, the source and the
        provisions (a dict from string to int) and astakosclient will create
        the corresponding commission. In case of success it returns
        commission's id (int). Otherwise it raises an AstakosClientException
        exception.

    **get_pending_commissions()**
        It returns the pending commissions (list of integers). In case of
        error it raises an AstakosClientException exception.

    **get_commission_info(**\ serial\ **)**
        Given the id of a pending commission return a dict of dicts containting
        informations (details) about the requested commission.  In case of
        error it raises an AstakosClientException exception.

    **commission_action(**\ serial, action\ **)**
        Given the id of a pending commission, request the specified action
        (currently one of accept, reject).  In case of success it returns
        nothing.  Otherwise it raises an AstakosClientException exception.

    **accept_commission(**\ serial\ **)**
        Accept a pending commission (see commission_action).

    **reject_commission(**\ serial\ **)**
        Reject a pending commission (see commission_action).

    **resolve_commissions(**\ accept_serials, reject_serials\ **)**
        Accept or Reject many pending commissions at once.  In case of success
        return a dict of dicts describing which commissions accepted, which
        rejected and which failed to resolved. Otherwise raise an
        AstakosClientException exception.

    **get_projects(**\ name=None, state=None, owner=None\ **)**
        Retrieve all accessible projects

    **get_project(**\ project_id\ **)**
        Retrieve project description, if accessible

    **create_project(**\ specs\ **)**
        Submit application to create a new project

    **modify_project(**\ project_id, specs\ **)**
        Submit application to modify an existing project

    **project_action(**\ project_id, action, reason=""\ **)**
        Perform action on a project

    **get_applications(**\ project=None\ **)**
        Retrieve all accessible applications

    **get_application(**\ app_id\ **)**
        Retrieve application description, if accessible

    **application_action(**\ app_id, action, reason=""\ **)**
        Perform action on an application

    **get_memberships(**\ project=None\ **)**
        Retrieve all accessible memberships

    **get_membership(**\ memb_id\ **)**
        Retrieve membership description, if accessible

    **membership_action(**\ memb_id, action, reason=""\ **)**
        Perform action on a membership

    **join_project(**\ project_id\ **)**
        Join a project

    **enroll_member(**\ project_id, email\ **)**
        Enroll a user in a project

Public Functions
----------------

**get_token_from_cookie(**\ request, cookie_name\ **)**
    Given a Django request object and an Astakos cookie name
    extract the user's token from it.

**parse_endpoints(**\ endpoints, ep_name=None, ep_type=None, ep_region=None, ep_version_id=None\ **)**
    Parse the endpoints (acquired using *get_endpoints*) and extract the ones
    needed.  Return only the endpoints that match all of the given criterias.
    If no match is found then raise NoEndpoints exception.


Exceptions and Errors
=====================

*exception* **AstakosClientException**
    Raised in case of an error. It contains an error message and the
    corresponding http status code. Other exceptions raised by astakosclient
    module are derived from this one.

*exception* **BadValue**
    A redefinition of ValueError exception under AstakosClientException.

*exception* **InvalidResponse**
    This exception is raised whenever the server's response is not valid json
    (cannot be parsed by simplejson library).

*exception* **BadRequest**
    Raised in case of a Bad Request, with status 400.

*exception* **Unauthorized**
    Raised in case of Invalid token (unauthorized access), with status 401.

*exception* **Forbidden**
    The server understood the request, but is refusing to fulfill it. Status
    401.

*exception* **NotFound**
    The server has not found anything matching the Request-URI. Status 404.

*exception* **QuotaLimit**
    Quantity fell below zero or exceeded capacity in one of the holdings.

*exception* **NoUserName**
    Raised by getDisplayName and getServiceDisplayName when an invalid UUID was
    given.

*exception* **NoUUID**
    Raised by *getUUID* and *getServiceUUID* when an invalid username was
    given.

*exception* **NoEndpoints**
    Raised by *parse_endpoints* when no endpoints found matching the given
    criteria.
