Weblogin API
============

This is Weblogin API guide.

Login
^^^^^
This service is used by Okeanos services' clients in order to acquire the user authentication token.

The login URI accepts the following parameters:

========== ====== ===============
URI        Method Description
========== ====== ===============
``/login`` GET    Authenticate user and return authentication token
========== ====== ===============

|

======================  =========================
Request Parameter Name  Value
======================  =========================
next                    The URI to redirect to when the process is finished
renew                   Force token renewal (no value parameter)
force                   Force session invalidation (no value parameter)
======================  =========================

If the request user is not authenticated, is sent to the login view and
after successful login, is redirected back to this view.

If the request user has not signed the approval terms, is sent to the approval terms view and
after successfully signing the terms, is redirected to back to this view.

Finally, if the request user is authenticated and has signed the approval terms,
is redirected to the `next` request parameter value.

The resulted URI contains the user identifier and authentication token.

=========================== =====================
Return Code                 Description
=========================== =====================
302 (Redirect)
400 (Bad Request)           Missing ``next`` parameter
403 (Unauthorized)          The ``next`` parameter is beyond the allowed schemes (set by ASTAKOS_REDIRECT_ALLOWED_SCHEMES setting)
=========================== =====================
