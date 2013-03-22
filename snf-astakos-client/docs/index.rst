.. _snf-astakos-client:

Component snf-astakos-client
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Synnefo component :ref:`snf-astakos-client <snf-astakos-client>` defines a
default client for the :ref:`Astakos <astakos>` service. It is designed to be
simple and minimal, hence easy to debug and test.

It uses the user's authentication token to query Astakos for:

    * User's info
    * Usernames for given UUIDs
    * UUIDs for given usernames

It can also query Astakos with another service's (Cyclades or Pithos)
authentication token for:

    * Usernames for given UUIDs
    * UUIDs for given usernames

Additionally, there are options for using the `objpool
<https://github.com/grnet/objpool>`_ library to pool the http connections.


Basic example
=============

The ``astakosclient`` module provides the ``AstakosClient`` class. This section
demonstrates how to get user's info using ``astakosclient``.

.. code-block:: python

    from astakosclient import AstakosClient

    client = AstakosClient("https://accounts.example.com")
    user_info = client.getUserInfo("UQpYas7ElzWGD5yCcEXtjw==")
    print user_info['username']

Another example where we ask for the username of a user with UUID:
``b3de8eb0-3958-477e-als9-789af8dd352c``

.. code-block:: python

    from astakosclient import AstakosClient

    client = AstakosClient("https://accounts.example.com")
    username = client.getDisplayName("UQpYas7ElzWGD5yCcEXtjw==",
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

    **getUserInfo(**\ token, usage=False\ **)**
        Given a valid authentication token it returns a dict with the
        correspoinding user's info. If usage is set to True more
        information about user's resources will be returned.
        In case of error raise an AstakosClientException exception.

    **getDisplayNames(**\ token, uuids\ **)**
        Given a valid authentication token and a list of UUIDs
        return a uuid_catalog, that is a dictionary with the given
        UUIDs as keys and the corresponding user names as values.
        Invalid UUIDs will not be in the dictionary.
        In case of error raise an AstakosClientException exception.

    **getDisplayName(**\ token, uuid\ **)**
        Given a valid authentication token and a UUID (as string)
        return the corresponding user name (as string).
        In case of invalid UUID raise NoDisplayName exception.
        In case of error raise an AstakosClientException exception.

    **getServiceDisplayNames(**\ token, uuids\ **)**
        Same as getDisplayNames but called with a service's token.

    **getServiceDisplayName(**\ token, uuid\ **)**
        Same as getDisplayName but called with a service's token.

    **getUUIDs(**\ token, display_names\ **)**
        Given a valid authentication token and a list of usernames
        return a displayname_catalog, that is a dictionary with the given
        usernames as keys and the corresponding UUIDs as values.
        Invalid usernames will not be in the dictionary.
        In case of error raise an AstakosClientException exception.

    **getUUID(**\ token, display_name\ **)**
        Given a valid authentication token and a username (as string)
        return the corresponding UUID (as string).
        In case of invalid user name raise NoUUID exception.
        In case of error raise an AstakosClientException exception.

    **getServiceUUIDs(**\ token, uuids\ **)**
        Same as getUUIDs but called with a service's token.

    **getServiceUUID(**\ token, uuid\ **)**
        Same as getUUID but called with a service's token.

    **getServices()**
        Return a list of dicts with the registered services.


Public Functions
----------------

**getTokenFromCookie(**\ request, cookie_name\ **)**
    Given a Django request object and an Astakos cookie name
    extract the user's token from it.


Exceptions and Errors
=====================

*exception* **AstakosClientException**
    Raised in case of an error. It contains an error message and the
    corresponding http status code. Other exceptions raise by astakosclient
    module are derived from this one.

*exception* **BadRequest**
    Raised in case of a Bad Request, with status 400.

*exception* **Unauthorized**
    Raised in case of Invalid token (unauthorized access), with status 401.

*exception* **Forbidden**
    The server understood the request, but is refusing to fulfill it.
    Status 401.

*exception* **NotFound**
    The server has not found anything matching the Request-URI. Status 404.

*exception* **NoDisplayName**
    Raised by getDisplayName and getServiceDisplayName when an invalid
    UUID was given.

*exception* **NoUUID**
    Raised by *getUUID* and *getServiceUUID* when an invalid
    username was given.
