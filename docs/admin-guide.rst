.. _admin-guide:

Synnefo Administrator's Guide
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is the complete Synnefo Administrator's Guide.


.. _syn+archip:

General Synnefo Architecture
============================

The following figure shows a detailed view of the whole Synnefo architecture
and how it interacts with multiple Ganeti clusters. We hope that after reading
the Administrator's Guide you will be able to understand every component and
all the interactions between them.

.. image:: images/synnefo-arch2.png
   :width: 100%
   :target: _images/synnefo-arch2.png

Synnefo also supports RADOS as an alternative storage backend for
Files/Images/VM disks. You will find the :ref:`corresponding figure
<syn+archip+rados>` later in this guide.


Identity Service (Astakos)
==========================


Authentication methods
----------------------

Astakos supports multiple authentication methods:

 * local username/password
 * LDAP / Active Directory
 * SAML 2.0 (Shibboleth) federated logins
 * Google
 * Twitter
 * LinkedIn

.. _shibboleth-auth:

Shibboleth Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~

Astakos can delegate user authentication to a Shibboleth federation.

To setup shibboleth, install package::

  apt-get install libapache2-mod-shib2

Change appropriately the configuration files in ``/etc/shibboleth``.

Add in ``/etc/apache2/sites-available/synnefo-ssl``::

  ShibConfig /etc/shibboleth/shibboleth2.xml
  Alias      /shibboleth-sp /usr/share/shibboleth

  <Location /ui/login/shibboleth>
    AuthType shibboleth
    ShibRequireSession On
    ShibUseHeaders On
    require valid-user
  </Location>

and before the line containing::

  ProxyPass        / http://localhost:8080/ retry=0

add::

  ProxyPass /Shibboleth.sso !

Then, enable the shibboleth module::

  a2enmod shib2

After passing through the apache module, the following tokens should be
available at the destination::

  eppn # eduPersonPrincipalName
  Shib-InetOrgPerson-givenName
  Shib-Person-surname
  Shib-Person-commonName
  Shib-InetOrgPerson-displayName
  Shib-EP-Affiliation
  Shib-Session-ID

Astakos keeps a map of shibboleth users using the value of the ``REMOTE_USER``
header, passed by the ``mod_shib2`` module. This happens in order to be able to
identify the astakos account the shibboleth user is associated to, every time
the user logs in from an affiliate shibboleth IdP. 

The shibboleth attribute which gets mapped to the ``REMOTE_USER`` header can be
changed in ``/etc/shibboleth/shibboleth2.xml`` configuration file.

.. code-block:: xml

    <!-- The ApplicationDefaults element is where most of Shibboleth's SAML bits are defined. -->
        <ApplicationDefaults entityID="https://sp.example.org/shibboleth" 
         REMOTE_USER="eppn persistent-id targeted-id">

.. warning::

 Changing ``mod_shib2`` ``REMOTE_USER`` to map to different shibboleth
 attributes will probably invalidate any existing shibboleth enabled users in
 astakos database. Those users won't be able to login to their existing accounts.


Finally, add 'shibboleth' in ``ASTAKOS_IM_MODULES`` list. The variable resides
inside the file ``/etc/synnefo/20-snf-astakos-app-settings.conf``

Twitter Authentication
~~~~~~~~~~~~~~~~~~~~~~

To enable twitter authentication while signed in under a Twitter account,
visit dev.twitter.com/apps.

Click Create an application.

Fill the necessary information and for callback URL give::

    https://node1.example.com/ui/login/twitter/authenticated

Finally, add 'twitter' in ``ASTAKOS_IM_MODULES`` list. The variable resides
inside the file ``/etc/synnefo/20-snf-astakos-app-settings.conf``

Google Authentication
~~~~~~~~~~~~~~~~~~~~~

To enable google authentication while signed in under a Google account,
visit https://code.google.com/apis/console/.

Under API Access select Create another client ID, select Web application,
expand more options in Your site or hostname section and in Authorized
Redirect URIs add:


Fill the necessary information and for callback URL give::

    https://node1.example.com/ui/login/google/authenticated

Finally, add 'google' in ``ASTAKOS_IM_MODULES`` list. The variable resides
inside the file ``/etc/synnefo/20-snf-astakos-app-settings.conf``


Working with Astakos
--------------------

User registration
~~~~~~~~~~~~~~~~~

When a new user signs up, he/she is not directly marked as active. You can see
his/her state by running (on the machine that runs the Astakos app):

.. code-block:: console

   $ snf-manage user-list

More detailed user status is provided in the `status` field of the `user-show`
command:

.. code-block:: console

  $ snf-manage user-show <user-id>

  id                  : 6
  uuid                : 78661411-5eed-412f-a9ea-2de24f542c2e
  status              : Accepted/Active (accepted policy: manual)
  email               : user@synnefo.org
  ....

Based on the `astakos-app` configuration, there are several ways for a user to
get verified and activated in order to be able to login. We discuss the user
verification and activation flow in the following section.

User activation flow
````````````````````

A user can register for an account using the astakos signup form. Once the form
is submited successfully a user entry is created in astakos database. That entry
is passed through the astakos activation backend which handles whether the user
should be automatically verified and activated.

Email verification
``````````````````

The verification process takes place in order to ensure that the user owns the
email provided during the signup process. By default, after each successful
signup astakos notifies user with an verification url via email.

At this stage:

    * subsequent registrations invalidate and delete the previous registrations
      of the same email address.

    * in case user misses the initial notification, additional emails can be
      send either via the url which is prompted to the user if he tries to
      login, or by the administrator using the ``snf-manage user-activation-send
      <userid>`` command.

    * administrator may also enforce a user to get verified using the
      ``snf-manage user-modify --verify <userid>`` command.

Account activation
``````````````````

Once the user gets verified, it is time for Astakos to decide whether or not to
proceed through user activation process. If ``ASTAKOS_MODERATION_ENABLED``
setting is set to ``False`` (default value) user gets activated automatically.

In case the moderation is enabled Astakos may still automatically activate the
user in the following cases:

    * User email matches any of the regular expressions defined in
      ``ASTAKOS_RE_USER_EMAIL_PATTERNS`` (defaults to ``[]``)
    * User used a signup method (e.g. ``shibboleth``) for which automatic
      activation is enabled (see
      :ref:`authentication methods policies <auth_methods_policies>`).

If all of the above fail to trigger automatic activation, an email is sent to
the persons listed in ``HELPDESK``, ``MANAGERS`` and ``ADMINS`` settings,
notifing that there is a new user pending for moderation and that it's up to
the administrator to decide if the user should be activated. The UI also shows
a corresponding 'pending moderation' message to the user. The administrator can
activate a user using the ``snf-manage user-modify`` command:

.. code-block:: console

    # command to activate a pending user
    $ snf-manage user-modify --accept <userid>

    # command to reject a pending user
    $ snf-manage user-modify --reject --reject-reason="spammer" <userid>

Once the activation process finishes, a greeting message is sent to the user
email address and a notification for the activation to the persons listed in
``HELPDESK``, ``MANAGERS`` and ``ADMINS`` settings. Once activated the user is
able to login and access the Synnefo services.

Additional authentication methods
`````````````````````````````````

Astakos supports third party logins from external identity providers. This
can be usefull since it allows users to use their existing credentials to
login to astakos service.

Currently astakos supports the following identity providers:

    * `Shibboleth <http://www.internet2.edu/shibboleth>`_ (module name
      ``shibboleth``)
    * `Google <https://developers.google.com/accounts/docs/OAuth2>`_ (module
      name ``google``)
    * `Twitter <https://dev.twitter.com/docs/auth>`_ (module name ``twitter``)
    * `LinkedIn <http://developer.linkedin.com/documents/authentication>`_
      (module name ``linkedin``)

To enable any of the above modules (by default only ``local`` accounts are
allowed), retrieve and set the required provider settings and append the
module name in ``ASTAKOS_IM_MODULES``.

.. code-block:: python

    # settings from https://code.google.com/apis/console/
    ASTAKOS_GOOGLE_CLIENT_ID = '1111111111-epi60tvimgha63qqnjo40cljkojcann3.apps.googleusercontent.com'
    ASTAKOS_GOOGLE_SECRET = 'tNDQqTDKlTf7_LaeUcWTWwZM'

    # let users signup and login using their google account
    ASTAKOS_IM_MODULES = ['local', 'google']


.. _auth_methods_policies:

Authentication method policies
``````````````````````````````

Astakos allows you to override the default policies for each enabled provider
separately by adding the approriate settings in your ``.conf`` files in the
following format:

**ASTAKOS_AUTH_PROVIDER_<module>_<policy>_POLICY**

Available policies are:

    * **CREATE** Users can signup using that provider (default: ``True``)
    * **REMOVE/ADD** Users can remove/add login method from their profile
      (default: ``True``)
    * **AUTOMODERATE** Automatically activate users that signup using that
      provider (default: ``False``)
    * **LOGIN** Whether or not users can use the provider to login (default:
      ``True``).

e.g. to enable automatic activation for your academic users, while keeping
locally signed up users under moderation you can apply the following settings.

.. code-block:: python

    ASTAKOS_AUTH_PROVIDER_SHIBBOLETH_AUTOMODERATE_POLICY = True
    ASTAKOS_AUTH_PROVIDER_SHIBBOLETH_REMOVE_POLICY = False

User login
~~~~~~~~~~

During the logging procedure, the user is authenticated by the respective
identity provider.

If ``ASTAKOS_RECAPTCHA_ENABLED`` is set and the user fails several times
(``ASTAKOS_RATELIMIT_RETRIES_ALLOWED`` setting) to provide the correct
credentials for a local account, he/she is then prompted to solve a captcha
challenge.

Upon success, the system renews the token (if it has expired), logins the user
and sets the cookie, before redirecting the user to the ``next`` parameter
value.

Projects and quota
~~~~~~~~~~~~~~~~~~

Synnefo supports granting resources and controling their quota through the
mechanism of *projects*. A project is considered as a pool of finite
resources. Every actual resources allocated by a user (e.g. a Cyclades VM or
a Pithos container) is also assigned to a project where the user is a
member to. For each resource a project specifies the maximum amount that can
be assigned to it and the maximum amount that a single member can assign to it.

Default quota
`````````````

Upon user creation, a special purpose user-specific project is automatically
created in order to hold the base quota provided by the system. These *base*
projects are identified with the same UUID as the user.

To inspect the quota that future users will receive by default through their
base projects, check column ``base_default`` in::

   # snf-manage resource-list

You can modify the default base quota limit for all future users with::

   # snf-manage resource-modify <resource_name> --base-default <value>

Grant extra quota through projects
``````````````````````````````````

A user can apply for a new project through the web interface or the API.
Once it is approved by the administrators, the applicant can join the
project and let other users in too.

A project member can make use of the quota granted by the project by
specifying this particular project when creating a new quotable entity.

Note that quota are not accumulative: in order to allocate a 100GB disk,
one must be in a project that grants at least 100GB; it is not possible to
add up quota from different projects. Note also that if allocating an entity
requires multiple resources (e.g. cpu and ram for a Cyclades VM) these must
be all assigned to a single project.

Control projects
````````````````

To list pending project applications in astakos::

    # snf-manage project-list --pending

Note the last column, the application id. To approve it::

    # <app id> from the last column of project-list
    # snf-manage project-control --approve <app id>

To deny an application::

    # snf-manage project-control --deny <app id>

Before taking an action, on can inspect project status, settings and quota
limits with::

   # snf-manage project-show <project-uuid>

For an initialized project, option ``--quota`` also reports the resource
usage.

Users designated as *project admins* can approve or deny
an application through the web interface. In
``20-snf-astakos-app-settings.conf`` set::

    # UUIDs of users that can approve or deny project applications from the web.
    ASTAKOS_PROJECT_ADMINS = [<uuid>, ...]

Set quota limits
````````````````

One can change the quota limits of an initialized project with::

   # snf-manage project-modify <project-uuid> --limit <resource_name> <member_limit> <project_limit>

One can set base quota for all accepted users (that is, set limits for base
project), with possible exceptions, with::

   # snf-manage project-modify --all-base-projects --exclude <uuid1>,<uuid2> --limit ...

Quota for a given resource are reported for all projects that the user is
member in with::

   # snf-manage user-show <user-uuid> --quota

With option ``--projects``, owned projects and memberships are also reported.

Astakos advanced operations
---------------------------

Adding "Terms of Use"
~~~~~~~~~~~~~~~~~~~~~

Astakos supports versioned terms-of-use. First of all you need to create an
html file that will contain your terms. For example, create the file
``/usr/share/synnefo/sample-terms.html``, which contains the following:

.. code-block:: console

   <h1>My cloud service terms</h1>

   These are the example terms for my cloud service

Then, add those terms-of-use with the snf-manage command:

.. code-block:: console

   $ snf-manage term-add /usr/share/synnefo/sample-terms.html

Your terms have been successfully added and you will see the corresponding link
appearing in the Astakos web pages' footer.

During the account registration, if there are approval terms, the user is
presented with an "I agree with the Terms" checkbox that needs to get checked
in order to proceed.

In case there are new approval terms that the user has not signed yet, the
``signed_terms_required`` view decorator redirects to the ``approval_terms``
view, so the user will be presented with the new terms the next time he/she
logins.

Enabling reCAPTCHA
~~~~~~~~~~~~~~~~~~

Astakos supports the `reCAPTCHA <http://www.google.com/recaptcha>`_ feature.
If enabled, it protects the Astakos forms from bots. To enable the feature, go
to https://www.google.com/recaptcha/admin/create and create your own reCAPTCHA
key pair. Then edit ``/etc/synnefo/20-snf-astakos-app-settings.conf`` and set
the corresponding variables to reflect your newly created key pair. Finally, set
the ``ASTAKOS_RECAPTCHA_ENABLED`` variable to ``True``:

.. code-block:: console

   ASTAKOS_RECAPTCHA_PUBLIC_KEY = 'example_recaptcha_public_key!@#$%^&*('
   ASTAKOS_RECAPTCHA_PRIVATE_KEY = 'example_recaptcha_private_key!@#$%^&*('

   ASTAKOS_RECAPTCHA_ENABLED = True

Restart the service on the Astakos node(s) and you are ready:

.. code-block:: console

   # /etc/init.d/gunicorn restart

Checkout your new Sign up page. If you see the reCAPTCHA box, you have setup
everything correctly.


Astakos internals
-----------------

X-Auth-Token
~~~~~~~~~~~~

Alice requests a specific resource from a cloud service e.g.: Pithos. In the
request she supplies the `X-Auth-Token` to identify whether she is eligible to
perform the specific task. The service contacts Astakos through its
``/account/v1.0/authenticate`` api call (see :ref:`authenticate-api-label`)
providing the specific ``X-Auth-Token``. Astakos checkes whether the token
belongs to an active user and it has not expired and returns a dictionary
containing user related information. Finally the service uses the ``uniq``
field included in the dictionary as the account string to identify the user
accessible resources.

.. _authentication-label:

Django Auth methods and Backends
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Astakos incorporates Django user authentication system and extends its User model.

Since username field of django User model has a limitation of 30 characters,
AstakosUser is **uniquely** identified by the ``email`` instead. Therefore,
``astakos.im.authentication_backends.EmailBackend`` is served to authenticate a
user using email if the first argument is actually an email, otherwise tries
the username.

A new AstakosUser instance is assigned with a uui as username and also with a
``auth_token`` used by the cloud services to authenticate the user.
``astakos.im.authentication_backends.TokenBackend`` is also specified in order
to authenticate the user using the email and the token fields.

Logged on users can perform a number of actions:

 * access and edit their profile via: ``/im/profile``.
 * change their password via: ``/im/password``
 * send feedback for grnet services via: ``/im/send_feedback``
 * logout (and delete cookie) via: ``/im/logout``

Internal Astakos requests are handled using cookie-based Django user sessions.

External systems should forward to the ``/login`` URI. The server,
depending on its configuration will redirect to the appropriate login page.
When done with logging in, the service's login URI should redirect to the URI
provided with next, adding user and token parameters, which contain the email
and token fields respectively.

The login URI accepts the following parameters:

======================  =========================
Request Parameter Name  Value
======================  =========================
next                    The URI to redirect to when the process is finished
renew                   Force token renewal (no value parameter)
force                   Force logout current user (no value parameter)
======================  =========================

External systems inside the ``ASTAKOS_COOKIE_DOMAIN`` scope can acquire the
user information by the cookie identified by ``ASTAKOS_COOKIE_NAME`` setting
(set during the login procedure).

Finally, backend systems having acquired a token can use the
:ref:`authenticate-api-label` API call from a private network or through HTTPS.


File/Object Storage Service (Pithos+)
====================================

Pithos+ is the Synnefo component that implements a storage service and exposes
the associated OpenStack REST APIs with custom extensions.

Pithos+ advanced operations
---------------------------

Enable separate domain for serving user content
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since Synnefo v0.15, there is a possibility to serve untrusted user content
in an isolated domain.

Enabling this feature consists of the following steps:

#. **Declare new domain in apache server**

   In order to enable the apache server to serve several domains it is required
   to setup several virtual hosts.
   Therefore, for adding the new domain e.g. "user-content.example.com", append
   the following in ``/etc/apache2/sites-available/synnefo-ssl``:

    .. code-block:: console

        <VirtualHost _default_:443>
            ServerName user-content.example.com

            Alias /static "/usr/share/synnefo/static"

            #  SetEnv no-gzip
            #  SetEnv dont-vary

           AllowEncodedSlashes On

           RequestHeader set X-Forwarded-Protocol "https"

        <Proxy * >
            Order allow,deny
            Allow from all
        </Proxy>

            SetEnv                proxy-sendchunked
            SSLProxyEngine        off
            ProxyErrorOverride    off

            ProxyPass        /static !
            ProxyPass        / http://localhost:8080/ retry=0
            ProxyPassReverse / http://localhost:8080/

            RewriteEngine On
            RewriteCond %{THE_REQUEST} ^.*(\\r|\\n|%0A|%0D).* [NC]
            RewriteRule ^(.*)$ - [F,L]

            SSLEngine on
            SSLCertificateFile    /etc/ssl/certs/ssl-cert-snakeoil.pem
            SSLCertificateKeyFile /etc/ssl/private/ssl-cert-snakeoil.key
        </VirtualHost>

    .. note:: Consider also to purchase and install a certificate for the new
              domain.


    Finally, restart the apache server::

        pithos-host$ /etc/init.d/apache2 restart

#. **Register Pithos+ as an OAuth2 client in Astakos**

   Starting from synnefo version 0.15, in order to view the content of a
   protected resource, Pithos+ (on behalf of the user) has to be granted
   authorization for the specific resource by Astakos.

   During the authorization grant procedure, Pithos+ has to authenticate
   itself with Astakos since the latter has to prevent serving requests by
   unknown/unauthorized clients.

   Therefore, in the installation guide you were guided to register Pithos+
   as an OAuth2 client in Astakos.

   .. note:: You can see the registered clients by running::
    astakos-host$ snf-manage oauth2-client-list -o identifier,redirect_urls,is_trusted

   However, requests originated from the new domain will be rejected since
   Astakos is ignorant about the new domain.

   Therefore, you need to register a new client pointing to the unsafe domain.
   To do so, use the following command::

        astakos-host$ snf-manage oauth2-client-add pithos-unsafe-domain --secret=<secret> --is-trusted --url https://user-content.example.com/pithos/ui/view


   .. note:: You can also unregister the client pointing to the safe domain,
       since it will no longer be useful.
       To do so, run the following::

        astakos-host$ snf-manage oauth2-client-remove pithos-view

#. **Update Pithos+ configuration**

   Respectively, the ``PITHOS_OAUTH2_CLIENT_CREDENTIALS`` setting should be
   updated to contain the credentials of the client registered in the previous
   step.

   Furthermore, you need to restrict all the requests for user content
   to be served exclusively by the unsafe domain.

   To enable this, set the ``PITHOS_UNSAFE_DOMAIN`` setting to the value
   of the new domain e.g. "user-content.example.com"

   Finally, restart the gunicorn server::

        pithos-host$ /etc/init.d/gunicorn restart


Compute/Network/Image Service (Cyclades)
========================================

Introduction
------------

Cyclades is the Synnefo component that implements Compute, Network and Image
services and exposes the associated OpenStack REST APIs. By running Cyclades
you can provide a cloud that can handle thousands of virtual servers and
networks.

Cyclades does not include any virtualization software and knows nothing about
the low-level VM management operations, e.g. the handling of VM creation or
migrations among physical nodes. Instead, Cyclades is the component that
handles multiple Ganeti backends and exposes the REST APIs. The administrator
can expand the infrastructure dynamically either by adding more Ganeti nodes
or by adding new Ganeti clusters. Cyclades issue VM control commands to Ganeti
via Ganeti's remote API and receive asynchronous notifications from Ganeti
backends whenever the state of a VM changes, due to Synnefo- or
administrator-initiated commands.

Cyclades is the action orchestrator and the API layer on top of multiple Ganeti
clusters. By this decoupled design, Ganeti cluster are self-contained and
the administrator has complete control on them without Cyclades knowing about
it. For example a VM migration to a different physical node is transparent
to Cyclades.

Working with Cyclades
---------------------

Flavors and Volume Types
~~~~~~~~~~~~~~~~~~~~~~~~

When creating a VM, the user must specify the `flavor` of the virtual server.
Flavors are the virtual hardware templates, and provide a description about
the number of CPUs, the amount of RAM, and the size of the disk of the VM.
Besides the size of the disk, Cyclades flavors describe the storage backend
that will be used for the virtual server.

Flavors are created by the administrator and the user can select one of the
available flavors. After VM creation, the user can resize his VM, by
adding/removing CPU and RAM.

Cyclades support different storage backends that are described by the `volume
type` of the flavor. Each volume type contains a `disk template` attribute
which is mapped to Ganeti's instance `disk template`.
Currently the available disk templates are the following:

* `file`: regulars file
* `sharedfile`: regular files on a shared directory, e.g. NFS
* `plain`: logical volumes
* `drbd`: drbd on top of lvm volumes
* `rbd`: rbd volumes residing inside a RADOS cluster
* `ext`: disks provided by an external shared storage.

  - `ext_archipelago`: External shared storage provided by
    `Archipelago <http://www.synnefo.org/docs/archipelago/latest/index.html>`_.

Volume types are created by the administrator using the `snf-manage
volume-type-create` command and providing the `disk template` and a
human-friendly name:

.. code-block:: console

 $ snf-manage volume-type-create --disk-template=drbd --name=DRBD

Flavors are created by the administrator using `snf-manage flavor-create`
command. The command takes as argument number of CPUs, amount of RAM, the size
of the disks and the volume type IDs and creates the flavors that belong to the
cartesian product of the specified arguments. For example, the following
command will create two flavors of `40G` disk size of volume type with ID `1`,
`4G` RAM and `2` or `4` CPUs.

.. code-block:: console

  $ snf-manage flavor-create 2,4 4096 40 1

To see the available flavors, run `snf-manage flavor-list` command. The
administrator can delete a flavor by using `flavor-modify` command:

.. code-block:: console

  $ snf-manage flavor-modify --deleted=True <flavor_id>

Finally, the administrator can set if new servers can be created from a flavor
or not, by setting the `allow_create` attribute:

.. code-block:: console

  $ snf-manage flavor-modify --allow-create=False <flavor_id>

Flavors that are marked with `allow_create=False` cannot be used by users to
create new servers. However, they can still be used to resize existing VMs.


Images
~~~~~~

When creating a VM the user must also specify the `image` of the virtual
server. Images are the static templates from which VM instances are
initiated. Cyclades uses Pithos to store system and user-provided images,
taking advantage of all Pithos features, like deduplication and syncing
protocol. An image is a file stored to Pithos with additional metadata that
are describing the image, e.g. the OS family or the root partition. To create
a new image, the administrator or the user has to upload it a file to Pithos,
and then register it as an Image with Cyclades. Then the user can use this
image to spawn new VMs from it.

Images can be private, public or shared between users, exactly like Pithos
files. Since user-provided public images can be untrusted, the administrator
can denote which users are trusted by adding them to the
``UI_SYSTEM_IMAGES_OWNERS`` setting in the
`/etc/synnefo/20-snf-cyclades-app-ui.conf` file. Images of those users are
properly displayed in the UI.

When creating a new VM, Cyclades pass the location of the image and it's
metadata to Ganeti. After Ganeti creates the instance's disk, `snf-image`
will copy the image to the new disk and perform the image customization
phase. During the phase, `snf-image` sends notifications to Cyclades about
the progress of the image deployment and customization. Customization includes
resizing the root file system, file injection (e.g. SSH keys) and setting
a custom hostname. For better understanding of `snf-image` read the
corresponding `documentation
<http://www.synnefo.org/docs/snf-image/latest/index.html>`_.

For passing sensitive data about the image to Ganeti, like the VMs password,
Cyclades keeps all sensitive data in memory caches (memcache) and never allows
them to hit the disk. The data are exposed to `snf-image` via an one-time URL
that is exposed from the `vmapi` application. So, instead of passing sensitive
data to `snf-image` via Ganeti, Cyclades pass an one-time configuration URL
that contains a random UUID. After `snf-image` gets the sensitive data, the
URL is invalidated so no one else can access them.

The administrator can register images, exactly like users, using a system user
(a user that is defined in the ``UI_SYSTEM_IMAGES_OWNERS`` setting). For
example, the following command will register the
`pithos://u53r-un1qu3-1d/images/debian_base-6.0-7-x86_64.diskdump` as an
image to Cyclades:

.. code-block:: console

 $ kamaki image register --name="Debian Base" \
        --location=pithos://u53r-un1qu3-1d/images/debian_base-6.0-7-x86_64.diskdump \
        --public \
        --disk-format=diskdump \
        --property OSFAMILY=linux --property ROOT_PARTITION=1 \
        --property description="Debian Squeeze Base System" \
        --property size=451 --property kernel=2.6.32 --property GUI="No GUI" \
        --property sortorder=1 --property USERS=root --property OS=debian

Deletion of an image is done via `kamaki image unregister` command, which will
delete the Cyclades Images but will leave the Pithos file as is (unregister).

Apart from using `kamaki` to see and hangle the available images, the
administrator can use `snf-manage image-list` and `snf-manage image-show`
commands to list and inspect the available public images. Also, the `--user-id`
option can be used the see the images of a specific user.

Virtual Servers
~~~~~~~~~~~~~~~

As mentioned, Cyclades uses Ganeti for management of VMs. The administrator can
handle Cyclades VMs just like any other Ganeti instance, via `gnt-instance`
commands. All Ganeti instances that belong to Synnefo, are separated from
others, by a prefix in their names. This prefix is defined in
``BACKEND_PREFIX_ID`` setting in
``/etc/synnefo/20-snf-cyclades-app-backend.conf``.

Apart from handling Cyclades VM at the Ganeti level, the administrator can
also use the `snf-manage server-*` commands. These command cover the most
common tasks that are relative with VM handling. Below we describe come
of them, but for more information you can use the `--help` option of all
`snf-manage server-* commands`. These command cover the most

The `snf-manage server-create` command can be used to create a new VM for some
user. This command can be useful when the administrator wants to test Cyclades
functionality without starting the API service, e.g. after an upgrade. Also, by
using `--backend-id` option, the VM will be created in the specified backend,
bypassing automatic VM allocation.

.. code-block:: console

 $ snf-manage server-create --flavor-id=1 --image-id=fc0f6858-f962-42ce-bf9a-1345f89b3d5e \
    --user-id=7cf4d078-67bf-424d-8ff2-8669eb4841ea --backend-id=2 \
    --password='example_passw0rd' --name='test_vm'

The above commnd will create a new VM for user
`7cf4d078-67bf-424d-8ff2-8669eb4841ea` in the Ganeti backend with ID 2. By
default this command will issue a Ganeti job to create the VM
(`OP_INSTANCE_CREATE`) and return. As in other commands, the `--wait=True`
option can be used in order to wait for the successful completion of the job.

`snf-manage server-list` command can be used to list all the available servers.
The command supports some useful options, like listing servers of a user,
listing servers that exist in a Ganeti backend and listing deleted servers.
Also, as in most of `*-list` commands, the `--filter-by` option can be used to
filter the results. For example, the following command will only display the
started servers of a specific flavor:

.. code-block:: console

 $ snf-manage server-list --filter-by="operstate=STARTED,flavor=<flavor_id>"

Another very useful command is the `server-inspect` command which will display
all available information about the state of the server in DB and the state
of the server in the Ganeti backend. The output will give you an easy overview
about the state of the VM which can be useful for debugging.

Also the administrator can `suspend` a user's VM, using the `server-modify`
command:

.. code-block:: console

 $ snf-manage server-modify --suspended=True <server_id>

The user is forbidden to do any action on an administratively suspended VM,
which is useful for abuse cases.

Ganeti backends
~~~~~~~~~~~~~~~

Since v0.11, Synnefo is able to manage multiple Ganeti clusters (backends)
making it capable to scale linearly to tens of thousands of VMs. Backends
can be dynamically added or removed via `snf-manage` commands.

Each newly created VM is allocated to a Ganeti backend by the Cyclades backend
allocator. The VM is "pinned" to this backend, and can not change through its
lifetime. The backend allocator decides in which backend to spawn the VM based
on the available resources of each backend, trying to balance the load between
them. Also, Networks are created to all Ganeti backends, in order to ensure
that VMs residing on different backends can be connected to the same networks.

A backend can be marked as `drained` in order to be excluded from automatic
servers allocation and not receive new servers. Also, a backend can be marked
as `offline` to denote that the backend is not healthy (e.g. broken master)
and avoid the penalty of connection timeouts.

Finally, Cyclades is able to manage Ganeti backends with different enabled
hypervisors (`kvm`, `xen`), and different enabled disk templates.

Listing existing backends
`````````````````````````
To list all the Ganeti backends known to Synnefo, we run:

.. code-block:: console

   $ snf-manage backend-list

Adding a new Ganeti backend
```````````````````````````
Backends are dynamically added under the control of Synnefo with `snf-manage
backend-add` command. In this section it is assumed that a Ganeti cluster,
named ``cluster.example.com`` is already up and running and configured to be
able to host Synnefo VMs.

To add this Ganeti cluster, we run:

.. code-block:: console

   $ snf-manage backend-add --clustername=cluster.example.com --user="synnefo_user" --pass="synnefo_pass"

where ``clustername`` is the Cluster hostname of the Ganeti cluster, and
``user`` and ``pass`` are the credentials for the `Ganeti RAPI user
<http://docs.ganeti.org/ganeti/2.8/html/rapi.html#users-and-passwords>`_.  All
backend attributes can be also changed dynamically using the `snf-manage
backend-modify` command.

``snf-manage backend-add`` will also create all existing public networks to
the new backend. You can verify that the backend is added, by running
`snf-manage backend-list`.

Note that no VMs will be spawned to this backend, since by default it is in a
``drained`` state after addition in order to manually verify the state of the
backend.

So, after making sure everything works as expected, make the new backend active
by un-setting the ``drained`` flag. You can do this by running:

.. code-block:: console

   $ snf-manage backend-modify --drained=False <backend_id>

Allocation of VMs in Ganeti backends
````````````````````````````````````
As already mentioned, the Cyclades backend allocator is responsible for
allocating new VMs to backends. This allocator does not choose the exact Ganeti
node that will host the VM but just the Ganeti backend. The exact node is
chosen by the Ganeti cluster's allocator (hail).

The decision about which backend will host a VM is based on the available
resources. The allocator computes a score for each backend, that shows its load
factor, and the one with the minimum score is chosen. The admin can exclude
backends from the allocation phase by marking them as ``drained`` by running:

.. code-block:: console

   $ snf-manage backend-modify --drained=True <backend_id>

The backend resources are periodically updated, at a period defined by
the ``BACKEND_REFRESH_MIN`` setting, or by running `snf-manage
backend-update-status` command. It is advised to have a cron job running this
command at a smaller interval than ``BACKEND_REFRESH_MIN`` in order to remove
the load of refreshing the backends stats from the VM creation phase.

Finally, the admin can decide to have a user's VMs being allocated to a
specific backend, with the ``BACKEND_PER_USER`` setting. This is a mapping
between users and backends. If the user is found in ``BACKEND_PER_USER``, then
Synnefo allocates all his/hers VMs to the specific backend in the variable,
even if is marked as drained (useful for testing).

.. _alloc_disk_templates:

Allocation based on disk-templates
**********************************

Besides the available resources of each Ganeti backend, the allocator takes
into consideration the disk template of the instance when trying to allocate it
to a Ganeti backend. Specifically, the allocator checks if the flavor of the
instance belongs to the available disk templates of each Ganeti backend.

A Ganeti cluster has a list of enabled disk templates
(`--enabled-disk-templates`) and a list of allowed disk templates for new
instances (`--ipolicy-disk-templates`). See the `gnt-cluster` manpage for more
details about these options.

When Synnefo allocates an instance, it checks whether the disk template of the
new instance belongs both in the enabled and ipolicy disk templates. You can
see the list of the available disk-templates by running `snf-manage
backend-list`. This list should be updated automatically after changing
these options in Ganeti and it can also be updated by running `snf-manage
backend-update-status`.

So the administrator, can route instances on different backends based on their
flavor disk template, by modifying the enabled or ipolicy disk templates of
each backend.  Also, the administrator can route instances between different
nodes of the same Ganeti backend, by modifying the same options at the
nodegroup level (see `gnt-group` manpage for mor details).

Removing an existing Ganeti backend
```````````````````````````````````
In order to remove an existing backend from Synnefo, you must first make
sure that there are not active servers in the backend, and then run:

.. code-block:: console

   $ snf-manage backend-remove <backend_id>


Virtual Networks
~~~~~~~~~~~~~~~~

Cyclades also implements the Network service and exposes the Quantum Openstack
API. Cyclades supports full IPv4 and IPv6 connectivity to the public internet
for it's VMs. Also, Cyclades provides L2 and L3 virtual private networks,
giving the user freedom to create arbitraty network topologies of
interconnected VMs.

Public networking is desployment specific and must be customized based on the
specific needs of the system administrator. Private virtual networks can be
provided by different network technologies which are exposed as different
network flavors. For better understanding of networking please refer to the
:ref:`Network <networks>` section.

A Cyclades virtual network is an isolated Layer-2 broadcast domain. A network
can also have an associated IPv4 and IPv6 subnet representing the Layer-3
characteristics of the network. Each subnet represents an IP address block
that is used in order to assign addresses to VMs.

To connect a VM to a network, a port must be created, which represent a virtual
port on a network switch. VMs are connected to networks by attaching a virtual
interface to a port.

Cyclades also supports `floating IPs`, which are public IPv4 addresses that
can dynamically(hotplug-able) be added and removed to VMs. Floating IPs are
a quotable resource that is allocated to each user. Unlike other cloud
platforms, floating IPs are not implemented using 1-1 NAT to a ports private
IP. Instead, floating IPs are directly assigned to virtual interfaces of VMs.

Exactly like VMS, networks can be handled as Ganeti networks via `gnt-network`
commands. All Ganeti networks that belong to Synnefo are named with the prefix
`${BACKEND_PREFIX_ID}-net-`. Also, there are a number of `snf-manage` commands
that can be used to handle `networks`, `subnets`, `ports` and `floating IPs`.
Below we will present a use case scenario using some of these commands. For
better understanding of these commands, refer to their help messages.

Create a virtual private network for user
`7cf4d078-67bf-424d-8ff2-8669eb4841ea` using the `PHYSICAL_VLAN` flavor, which
means that the network will be uniquely assigned a phsyical VLAN. The network
is assigned an IPv4 subnet, described by it's CIDR and gateway. Also,
the `--dhcp=True` option is used, to make `nfdhcpd` response to DHCP queries
from VMs.

.. code-block:: console

 $ snf-manage network-create --owner=7cf4d078-67bf-424d-8ff2-8669eb4841ea --name=prv_net-1 \
    --subnet=192.168.2.0/24 --gateway=192.168.2.1 --dhcp=True --flavor=PHYSICAL_VLAN

Inspect the state of the network in Cyclades DB and in all the Ganeti backends:

.. code-block:: console

  $ snf-manage network-inspect <network_id>

Inspect the state of the network's subnet, containg an overview of the
subnet's IPv4 address allocation pool:

.. code-block:: console

  $ snf-manage subnet-inspect <subnet_id>

Connect a VM to the created private network. The port will be automatically
be assigned an IPv4 address from one of the network's available IPs. This
command will result in sending an `OP_INSTANCE_MODIFY` Ganeti command and
attaching a NIC to the specified Ganeti instance.

.. code-block:: console

 $ snf-manage port-create --network=<network_id> --server=<server_id>

Inspect the state of the the port in Cyclades DB and in the Ganeti backend:

.. code-block:: console

 $ snf-manage port-inspect <port_id>

Disconnect the VM from the network and delete the network:

.. code-block:: console

 $ snf-manage port-remove <port_id>
 $ snf-manage network-remove <network_id>


Enabling DHCP
`````````````

When connecting a VM to a network, Cyclades will automatically assign an IPv4
address from the IPv4 or/and IPv6 subnets of the network. If the network has
no subnets, then it will not be assigned any IP address.

If the network has DHCP enabled, then `nfdhcpd` daemon, which must be running
on all Ganeti nodes, will respond to DHCP queries from VMs and assign to them
the IP address that was allocated by Cyclades. DCHP can be enabled/disabled
using the `--dhcp` option of `network-create` command.


Public network connectivity
```````````````````````````

Since v0.14, users are able to dynamically connect and disconnect their VMs
from public networks. In order to do that, they have to use a `floating IP`.
Floating IPs are basically public IPv4 addresses that can be dynamically
attached and detached from VMs. The user creates a floating IP address from a
network that has set the `floating_ip_pool` attribute. The floating IP is
accounted to the user, who can then connect his VMs to public networks by
creating ports that they are using this floating IP. Performing this work-flow
from `snf-manage` would look like this:

.. code-block:: console

 $ snf-manage network-list --filter-by="floating_ip_pool=True"
 id      name  user.uuid   state  public  subnet.ipv4  gateway.ipv4  drained  floating_ip_pool
 ---------------------------------------------------------------------------------------------
  1  Internet       None  ACTIVE    True  10.2.1.0/24      10.2.1.1    False              True

 $ snf-manage floating-ip-create --owner=7cf4d078-67bf-424d-8ff2-8669eb4841ea --network=1

 $ snf-manage floating-ip-list --user=7cf4d078-67bf-424d-8ff2-8669eb4841ea
 id   address       network                             user.uuid  server
 ------------------------------------------------------------------------
 38  10.2.1.2             1  7cf4d078-67bf-424d-8ff2-8669eb4841ea      42

 $ snf-manage port-create --owner=7cf4d078-67bf-424d-8ff2-8669eb4841ea --network=1 \
                          --ipv4-address=10.2.1.2 --floating-ip=38

 $ snf-manage port-list --user=7cf4d078-67bf-424d-8ff2-8669eb4841ea
 id                            user.uuid        mac_address  network  server_id  fixed_ips   state
 --------------------------------------------------------------------------------------------------
 163 7cf4d078-67bf-424d-8ff2-8669eb4841ea  aa:00:00:45:13:98       1         77   10.2.1.2  ACTIVE

 $ snf-manage port-remove 163
 $ snf-manage floating-ip-remove 38

Users do not have permission to connect and disconnect VMs from public
networks without using a floating IP address. However, the administrator
have the ability to perform this tasks, using `port-create` and `port-remove`
commands.

Network connectivity for newly created servers
``````````````````````````````````````````````

When creating a virtual server, the user can specify the networks that the
newly created server will be connected to. Beyond this, the administrator can
define a list of networks that every new server will be forced to connect to.
For example, you can enforce all VMs to be connected to a public network
containing a metadata server. The networks must be specified in the
``CYCLADES_FORCED_SERVER_NETWORKS`` that exists in the
``/etc/synnefo/20-snf-cyclades-app-api.conf``. For the networks in this
setting, no access control or quota policy are enforced!

Finally, the administrator can define a list of networks that new servers will
be connected, *if the user has not* specified networks in the request to create
the server. Access control and quota policy are enforced, just as if the user
had specified these networks. The list of these networks is defined in the
``CYCLADES_DEFAULT_SERVER_NETWORKS`` that exists in the
``/etc/synnefo/20-snf-cyclades-app-api.conf``. This setting should only
be used if Cyclades are being accessed by external clients that are
unaware of the `Neutron API extensions` in the `Compute API`.

Each member of the above mentioned settings can be:

* a network UUID
* a tuple of network UUIDs: the server will be connected to only one of these
  networks, e.g. one that has a free IPv4 address
* `SNF:ANY_PUBLIC_IPV4`: the server will be connected to any network with
  an IPv4 subnet defined
* `SNF:ANY_PUBLIC_IPV6`: the server will be connected to any network with
  only an IPv6 subnet defined.
* `SNF:ANY_PUBLIC`: the server will be connected to any public network.

Public IP accounting
````````````````````

There are many use cases, e.g. abuse ports, where you need to find which user
or which server had a public IP address. For this reason, Cyclades keeps track
usage of public IPv4/IPv6 addresses. Specifically, it keeps the date and time
that each public IP address was allocated and released from a virtual server.
This information can be found using `ip-list` command:

.. code-block:: console

 $ snf-manage ip-list

 Show usage of a specific address:
 $ snf-manage ip-list --address=192.168.2.1

 Show public IPs of a specific server:
 $ snf-manage ip-list --server=<server_id>


Managing Network Resources
``````````````````````````

Proper operation of the Cyclades Network Service depends on the unique
assignment of specific resources to each type of virtual network. Specifically,
these resources are:

* IP addresses. Cyclades creates a Pool of IPs for each Network, and assigns a
  unique IP address to each VM, thus connecting it to this Network. You can see
  the IP pool of each network by running `snf-manage subnet-inspect
  <subnet_ID>`. IP pools are automatically created and managed by Cyclades,
  depending on the subnet of the Network.
* Bridges corresponding to physical VLANs, which are required for networks of
  type `PRIVATE_PHYSICAL_VLAN`.
* One Bridge corresponding to one physical VLAN which is required for networks of
  type `PRIVATE_MAC_PREFIX`.

IPv4 addresses
**************

An allocation pool of IPv4 addresses is automatically created for every network
with an IPv4 subnet. By default, the allocation pool contains the range of IP
addresses that are included in the subnet, except from the gateway and the
broadcast address of the network. The range of IP addresses can be restricted
using the `--allocation-pool` option of `snf-manage network-create` command.
The admin can externally reserve IP addresses to exclude them from automatic
allocation with the `--add-reserved-ips` option of `snf-manage network-modify`
command. For example the following command will reserve two IP addresses from
network with ID `42`:

.. code-block:: console

 snf-manage network-modify --add-reserved-ips=10.0.0.21,10.0.0.22 42

.. warning:: Externally reserving IP addresses is also available at the Ganeti.
 However, when using Cyclades with multiple Ganeti backends, the handling of
 IP pools must be performed from Cyclades!

Bridges
*******

As already mentioned Cyclades use a pool of Bridges that must correspond
to Physical VLAN at the Ganeti level. A bridge from the pool is assigned to
each network of flavor `PHYSICAL_VLAN`. Creation of this pool is done
using `snf-manage pool-create` command. For example the following command
will create a pool containing the brdiges from `prv1` to `prv21`.

.. code-block:: console

   # snf-manage pool-create --type=bridge --base=prv --size=20

You can verify the creation of the pool, and check its contents by running:

.. code-block:: console

   # snf-manage pool-list
   # snf-manage pool-show --type=bridge 1

Finally you can use the `pool-modify` management command in order to externally
reserve the values from pool, extend or shrink the pool if possible.

MAC Prefixes
************

Cyclades also use a pool of MAC prefixes to assign to networks of flavor
`MAC_FILTERED`. The handling of this pool is done exactly as with pool of
bridges, except that the type option must be set to mac-prefix:

.. code-block:: console

   # snf-manage pool-create --type=mac-prefix --base=aa:00:0 --size=65536

The above command will create a pool of MAC prefixes from ``aa:00:1`` to
``b9:ff:f``. The MAC prefix pool is responsible for providing only unicast and
locally administered MAC addresses, so many of these prefixes will be
externally reserved, to exclude from allocation.

Quotas
~~~~~~

The andling of quotas for Cyclades resources is powered by Astakos quota
mechanism. During registration of Cyclades service to Astakos, the Cyclades
resources are also imported to Astakos for accounting and presentation.

Upon a request that will result in a resource creation or removal, Cyclades
will communicate with Astakos to ensure that user quotas are within limits and
update the corresponding usage. If a limit is reached, the request will be
denied with an `overLimit(413)` fault.

The resources that are exported by Cyclades are the following:

* `cyclades.vm`: Number of virtual machines
* `cyclades.total_cpu`: Number of virtual machine processors
* `cyclades.cpu`: Number of virtual machine processors of running VMs
* `cyclades.total_ram`: Virtual machine memory size
* `cyclades.ram`: Virtual machine memory size of running VMs
* `cyclades.disk`: Virtual machine disk size
* `cyclades.floating_ip`: Number of floating IP addresses
* `cyclades.network.private`: Number of private virtual networks

Enforcing quotas
~~~~~~~~~~~~~~~~

User quota can get overlimit, for example when a user is removed from a
project granting Cyclades resources. However, no action is automatically
taken to restrict users to their new limits. There is a special tool for
quota enforcement:

.. code-block:: console

  # snf-manage enforce-resources-cyclades

This command will check and report which users are overlimit on their
Cyclades quota; it will also suggest actions to be taken in order to enforce
quota limits, dependent on the overlimit resource:

* `cyclades.vm`: Delete VMs
* `cyclades.total_cpu`: Delete VMs
* `cyclades.cpu`: Shutdown VMs
* `cyclades.total_ram`: Delete VMs
* `cyclades.ram`: Shutdown VMs
* `cyclades.disk`: Delete VMs
* `cyclades.floating_ip`: Detach and remove IPs

VMs to be deleted/shutdown are chosen first by state in the following order:
ERROR, BUILD, STOPPED, STARTED or RESIZE and then by decreasing ID. When
needing to remove IPs, we first choose IPs that are free, then those
attached to VMs, using the same VM ordering.

By default, the command checks only the following resources: `cyclades.cpu`,
`cyclades.ram`, and `cyclades.floating_ip`; that is, the less dangerous
ones, those that do not result in *deleting* any VM. One can change the
default behavior by specifying the desired resources with option
``--resources``. It is also possible to specify users to be checked or
excluded.

Actual enforcement is done with option ``--fix``. In order to control the
load that quota enforcement may cause on Cyclades, one can limit the number
of operations per backend. For example,

.. code-block:: console

  # snf-manage enforce-resources-cyclades --fix --max-operations 10

will apply only the first 10 listed actions per backend. One can repeat the
operation, until nothing is left to be done.

To control load a timeout can also be set for shutting down VMs (using
option ``--shutdown-timeout <sec>``). This may be needed to avoid
expensive operations triggered by shutdown, such as Windows updates.

The command outputs the list of applied actions and reports whether each
action succeeded or not. Failure is reported if for any reason cyclades
failed to process the job and submit it to the backend.

Cyclades advanced operations
----------------------------

Reconciliation mechanism
~~~~~~~~~~~~~~~~~~~~~~~~

Cyclades - Ganeti reconciliation
````````````````````````````````

On certain occasions, such as a Ganeti or RabbitMQ failure, the state of
Cyclades database may differ from the real state of VMs and networks in the
Ganeti backends. The reconciliation process is designed to synchronize the
state of the Cyclades DB with Ganeti. There are two management commands for
reconciling VMs and Networks that will detect stale, orphans and out-of-sync
VMs and networks. To fix detected inconsistencies, use the `--fix-all`.

.. code-block:: console

  $ snf-manage reconcile-servers
  $ snf-manage reconcile-servers --fix-all

  $ snf-manage reconcile-networks
  $ snf-manage reconcile-networks --fix-all

Please see ``snf-manage reconcile-servers --help`` and ``snf-manage
reconcile--networks --help`` for all the details.


Cyclades - Astakos reconciliation
`````````````````````````````````

As already mentioned, Cyclades communicates with Astakos for resource
accounting and quota enforcement. In rare cases, e.g. unexpected
failures, the two services may get unsynchronized. For this reason there
are the `reconcile-commissions-cyclades` and `reconcile-resources-cyclades`
command that will synchronize the state of the two services. The first
command will detect any pending commissions, while the second command will
detect that the usage that is reported by Astakos is correct.
To fix detected inconsistencies, use the `--fix` option.

.. code-block:: console

  $ snf-manage reconcile-commissions-cyclades
  $ snf-manage reconcile-commissions-cyclades --fix

  $ snf-manage reconcile-resources-cyclades
  $ snf-manage reconcile-resources-cyclades --fix


Cyclades resources reconciliation
`````````````````````````````````

Reconciliation of pools will check the consistency of available pools by
checking that the values from each pool are not used more than once, and also
that the only reserved values in a pool are the ones used. Pool reconciliation
will check pools of bridges, MAC prefixes, and IPv4 addresses for all networks.
To fix detected inconsistencies, use the `--fix` option.


.. code-block:: console

  $ snf-manage reconcile-pools
  $ snf-manage reconcile-pools --fix

.. _admin-guide-stats:

VM stats collecting
~~~~~~~~~~~~~~~~~~~

snf-cyclades-gtools comes with a collectd plugin to collect CPU and network
stats for Ganeti VMs and an example collectd configuration. snf-stats-app is a
Django (snf-webproject) app that serves the VM stats graphs by reading the VM
stats (from RRD files) and serves graphs.

The snf-stats-app was originally written by `GRNET NOC <http://noc.grnet.gr>`_
as a WSGI Python app and was ported to a Synnefo (snf-webproject) app.

snf-stats-app configuration
```````````````````````````

The snf-stats-app node should have collectd installed. The collectd
configuration should enable the network plugin, assuming the server role, and
the RRD plugin / backend, to store the incoming stats. Your
``/etc/collectd/collectd.conf`` should look like:

.. code-block:: console

    FQDNLookup true
    LoadPlugin syslog
    <Plugin syslog>
        LogLevel info
    </Plugin>

    LoadPlugin network
    LoadPlugin rrdtool
    <Plugin network>
        TimeToLive 128
        <Listen "okeanos.io" "25826">
            SecurityLevel "Sign"
            AuthFile "/etc/collectd/passwd"
        </Listen>

        ReportStats false
        MaxPacketSize 65535
    </Plugin>


    <Plugin rrdtool>
        DataDir "/var/lib/collectd/rrd"
        CacheTimeout 120
        CacheFlush 900
        WritesPerSecond 30
        RandomTimeout 0
    </Plugin>

    Include "/etc/collectd/filters.conf"
    Include "/etc/collectd/thresholds.conf"


An example collectd config file is provided in
``/usr/share/doc/snf-stats-app/examples/stats-colletcd.conf``.

The recommended deployment is to run snf-stats-app using gunicorn with an
Apache2 or nginx reverse proxy (using the same configuration as the other
Synnefo services / apps). An example gunicorn config file is provided in
``/usr/share/doc/snf-stats-app/examples/stats.gunicorn``.

Make sure to edit the settings under
``/etc/synnefo/20-snf-stats-app-settings.conf`` to match your deployment.
More specifically, you should change the ``STATS_BASE_URL`` setting (refer
to previous documentation on the BASE_URL settings used by the other Synnefo
services / apps) and the ``RRD_PREFIX`` and ``GRAPH_PREFIX`` settings.

You should also set the ``STATS_SECRET_KEY`` to a random string and make sure
it's the same at the ``CYCLADES_STATS_SECRET_KEY`` on the Cyclades host (see
below).

``RRD_PREFIX`` is the directory where collectd stores the RRD files. The
default setting matches the default RRD directory for the collectd RRDtool
plugin. In a more complex setup, the collectd daemon could run on a separate
host and export the RRD directory to the snf-stats-app node via e.g. NFS.

``GRAPH_PREFIX`` is the directory where collectd stores the resulting
stats graphs. You should create it manually, in case it doesn't exist.

.. code-block::

    # mkdir /var/cache/snf-stats-app/
    # chown www-data:wwwdata /var/cache/snf-stats-app/

The snf-stats-app will typically run as the ``www-data`` user. In that case,
make sure that the ``www-data`` user should have read access to the
``RRD_PREFIX`` directory and read / write access to the ``GRAPH_PREFIX``
directory.

snf-stats-app, based on the ``STATS_BASE_URL`` setting will export the
following URL 'endpoints`:
 * CPU stats bar: ``STATS_BASE_URL``/v1.0/cpu-bar/<encrypted VM hostname>
 * Network stats bar: ``STATS_BASE_URL``/v1.0/net-bar/<encrypted VM hostname>
 * CPU stats daily graph: ``STATS_BASE_URL``/v1.0/cpu-ts/<encrypted VM hostname>
 * Network stats daily graph: ``STATS_BASE_URL``/v1.0/net-ts/<encrypted VM hostname>
 * CPU stats weekly graph: ``STATS_BASE_URL``/v1.0/cpu-ts-w/<encrypted VM hostname>
 * Network stats weekly graph: ``STATS_BASE_URL``/v1.0/net-ts-w/<encrypted VM hostname>

You can verify that these endpoints are exported by issuing:

.. code-block::

    # snf-manage show_urls

snf-cyclades-gtools configuration
`````````````````````````````````

To enable VM stats collecting, you will need to:
 * Install collectd on the every Ganeti (VM-capable) node.
 * Enable the Ganeti stats plugin in your collectd configuration. This can be
   achived by either copying the example collectd conf file that comes with
   snf-cyclades-gtools
   (``/usr/share/doc/snf-cyclades-gtools/examples/ganeti-stats-collectd.conf``)
   or by adding the following line to your existing (or default) collectd
   conf file:

       Include /etc/collectd/ganeti-stats.conf

   In the latter case, make sure to configure collectd to send the collected
   stats to your collectd server (via the network plugin). For more details on
   how to do this, check the collectd example config file provided by the
   package and the collectd documentation.

snf-cyclades-app configuration
``````````````````````````````

At this point, stats collecting should be enabled and working. You can check
that everything is ok by checking the contents of ``/var/lib/collectd/rrd/``
directory (it will gradually get populated with directories containing RRD
files / stats for every Synnefo instances).

You should also check that gunicorn and Apache2 are configured correctly by
accessing the graph URLs for a VM (whose stats have been populated in
``/var/lib/collectd/rrd``).

Cyclades uses the ``CYCLADES_STATS_SECRET_KEY`` setting in
``20-snf-cyclades-app`` to encrypt the instance hostname in the stats graph
URL. This settings should be set to a random value and match the
``STATS_SECRET_KEY`` on the Stats host.

Cyclades (snf-cyclades-app) fetches the stat graphs for VMs based on four
settings in ``20-snf-cyclades-app-api.conf``. The settings are:

 * CPU_BAR_GRAPH_URL = 'https://stats.host/stats/v1.0/cpu-bar/%s'
 * CPU_TIMESERIES_GRAPH_URL = 'https://stats.host/stats/v1.0/cpu-ts/%s'
 * NET_BAR_GRAPH_URL = 'https://stats.host/stats/v1.0/net-bar/%s'
 * NET_TIMESERIES_GRAPH_URL = 'https://stats.host/stats/v1.0/net-ts/%s'

Make sure that you change this settings to match your ``STATS_BASE_URL``
(and generally the Apache2 / gunicorn deployment on your stats host).

Cyclades will pass these URLs to the Cyclades UI and the user's browser will
fetch them when needed.


Helpdesk
--------

Helpdesk application provides the ability to view the virtual servers and
networks of all users, along with the ability to perform some basic actions
like administratively suspending a server. You can perform look-ups by
user UUID or email, by server ID (vm-$id) or by an IPv4 address.

If you want to activate the helpdesk application you can set to `True` the
`HELPDESK_ENABLED` setting. Access to helpdesk views (under
`$BASE_URL/helpdesk`) is only to allowed to users that belong to Astakos
groups defined in the `HELPDESK_PERMITTED_GROUPS` setting, which by default
contains the `helpdesk` group. For example, to allow <user_id>
to access helpdesk view, you should run the following command in the Astakos
node:

.. code-block:: console

 snf-manage group-add helpdesk
 snf-manage user-modify --add-group=helpdesk <user_id>


Cyclades internals
------------------

Asynchronous communication with Ganeti backends
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Synnefo uses Google Ganeti backends for VM cluster management. In order for
Cyclades to be able to handle thousands of user requests, Cyclades and Ganeti
communicate asynchronously. Briefly, requests are submitted to Ganeti through
Ganeti's RAPI/HTTP interface, and then asynchronous notifications about the
progress of Ganeti jobs are being created and pushed upwards to Cyclades. The
architecture and communication with a Ganeti backend is shown in the graph
below:

.. image:: images/cyclades-ganeti-communication.png
   :width: 40%
   :target: _images/cyclades-ganeti-communication.png

The Cyclades API server is responsible for handling user requests. Read-only
requests are directly served by looking up the Cyclades DB. If the request
needs an action in the Ganeti backend, Cyclades submit jobs to the Ganeti
master using the `Ganeti RAPI interface
<http://docs.ganeti.org/ganeti/2.8/html/rapi.html>`_.

While Ganeti executes the job, `snf-ganeti-eventd`, and `snf-progress-monitor`
are monitoring the progress of the job and send corresponding messages to the
RabbitMQ servers. These components are part of `snf-cyclades-gtools` and must
be installed on all Ganeti nodes. Specially:

* *snf-ganeti-eventd* sends messages about operations affecting the operating
  state of instances and networks. Works by monitoring the Ganeti job queue.
* *snf-progress_monitor* sends messages about the progress of the Image deployment
  phase which is done by the Ganeti OS Definition `snf-image`.

Finally, `snf-dispatcher` consumes messages from the RabbitMQ queues, processes
these messages and properly updates the state of the Cyclades DB. Subsequent
requests to the Cyclades API, will retrieve the updated state from the DB.


List of all Synnefo components
==============================

They are also available from our apt repository: ``apt.dev.grnet.gr``

 * `snf-common <http://www.synnefo.org/docs/snf-common/latest/index.html>`_
 * `snf-webproject <http://www.synnefo.org/docs/snf-webproject/latest/index.html>`_
 * `snf-astakos-app <http://www.synnefo.org/docs/astakos/latest/index.html>`_
 * `snf-pithos-backend <http://www.synnefo.org/docs/pithos/latest/backends.html>`_
 * `snf-pithos-app <http://www.synnefo.org/docs/pithos/latest/index.html>`_
 * `snf-pithos-webclient <http://www.synnefo.org/docs/pithos-webclient/latest/index.html>`_
 * `snf-cyclades-app <http://www.synnefo.org/docs/snf-cyclades-app/latest/index.html>`_
 * `snf-cyclades-gtools <http://www.synnefo.org/docs/snf-cyclades-gtools/latest/index.html>`_
 * `astakosclient <http://www.synnefo.org/docs/astakosclient/latest/index.html>`_
 * `snf-vncauthproxy <https://code.grnet.gr/projects/vncauthproxy>`_
 * `snf-image <http://www.synnefo.org/docs/snf-image/latest/index.html/>`_
 * `snf-image-creator <http://www.synnefo.org/docs/snf-image-creator/latest/index.html>`_
 * `snf-occi <http://www.synnefo.org/docs/snf-occi/latest/index.html>`_
 * `snf-cloudcms <http://www.synnefo.org/docs/snf-cloudcms/latest/index.html>`_
 * `nfdhcpd <https://code.grnet.gr/projects/nfdhcpd>`_


Synnefo management commands ("snf-manage")
==========================================

Each Synnefo service, Astakos, Pithos and Cyclades are controlled by the
administrator using the "snf-manage" admin tool. This tool is an extension of
the Django command-line management utility. It is run on the host that runs
each service and provides different types of commands depending the services
running on the host. If you are running more than one service on the same host
"snf-manage" adds all the corresponding commands for each service dynamically,
providing a unified admin environment.

To run "snf-manage" you just type:

.. code-block:: console

   # snf-manage <command> [arguments]

on the corresponding host that runs the service. For example, if you have all
services running on different physical hosts you would do:

.. code-block:: console

   root@astakos-host # snf-manage <astakos-command> [argument]
   root@pithos-host # snf-manage <pithos-command> [argument]
   root@cyclades-host # snf-manage <cyclades-command> [argument]

If you have all services running on the same host you would do:

.. code-block:: console

   root@synnefo-host # snf-manage <{astakos,pithos,cyclades}-command> [argument]

Note that you cannot execute a service's command on a host that is not running
this service. For example, the following will return an error if Astakos and
Cyclades are installed on different physical hosts:

.. code-block:: console

   root@astakos-host # snf-manage <cyclades-command> [argument]
   Unknown command: 'cyclades-command'
   Type 'snf-manage help' for usage.

This is the complete list of "snf-manage" commands for each service.

Astakos snf-manage commands
---------------------------

============================  ===========================
Name                          Description
============================  ===========================
fix-superusers                Transform superusers created by syncdb into AstakosUser instances
cleanup-full                  Cleanup sessions and session catalog
commission-list               List pending commissions
commission-show               Show details for a pending commission
component-add                 Register a component
component-list                List components
component-modify              Modify component attributes
component-show                Show component details
project-control               Manage projects and applications
project-list                  List projects
project-show                  Show project details
quota-list                    List user quota
quota-verify                  Check the integrity of user quota
reconcile-resources-astakos   Reconcile resource usage of Quotaholder with Astakos DB
resource-list                 List resources
resource-modify               Modify a resource's default base quota and boolean flags
service-export-astakos        Export Astakos services and resources in JSON format
service-import                Register services
service-list                  List services
service-show                  Show service details
term-add                      Add approval terms
user-activation-send          Send user activation
user-add                      Add user
authpolicy-add                Create a new authentication provider policy profile
authpolicy-list               List existing authentication provider policy profiles
authpolicy-remove             Remove an authentication provider policy
authpolicy-set                Assign an existing authentication provider policy profile to a user or group
authpolicy-show               Show authentication provider profile details
group-add                     Create a group with the given name
group-list                    List available groups
user-list                     List users
user-modify                   Modify user
user-show                     Show user details
oauth2-client-add             Create an oauth2 client
oauth2-client-list            List oauth2 clients
oauth2-client-remove          Remove an oauth2 client along with its registered redirect urls
============================  ===========================

Pithos snf-manage commands
--------------------------

============================  ===========================
Name                          Description
============================  ===========================
reconcile-commissions-pithos  Display unresolved commissions and trigger their recovery
service-export-pithos         Export Pithos services and resources in JSON format
reconcile-resources-pithos    Detect unsynchronized usage between Astakos and Pithos DB resources and synchronize them if specified so.
file-show                     Display object information
============================  ===========================

Cyclades snf-manage commands
----------------------------

============================== ===========================
Name                           Description
============================== ===========================
backend-add                    Add a new Ganeti backend
backend-list                   List backends
backend-modify                 Modify a backend
backend-update-status          Update backend statistics for instance allocation
backend-remove                 Remove a Ganeti backend
enforce-resources-cyclades     Check and fix quota violations for Cyclades resources
server-create                  Create a new server
server-show                    Show server details
server-list                    List servers
server-modify                  Modify a server
server-import                  Import an existing Ganeti VM into synnefo
server-inspect                 Inspect a server in DB and Ganeti
network-create                 Create a new network
network-list                   List networks
network-modify                 Modify a network
network-inspect                Inspect network state in DB and Ganeti
network-remove                 Delete a network
flavor-create                  Create a new flavor
flavor-list                    List flavors
flavor-modify                  Modify a flavor
volume-type-create             Create a new volume type
volume-type-list               List volume types
volume-type-show               Show volume type details
volume-type-modify             Modify a volume type
image-list                     List images
image-show                     Show image details
pool-create                    Create a bridge or mac-prefix pool
pool-show                      Show pool details
pool-list                      List pools
pool-modify                    Modify a pool
pool-remove                    Delete a pool
port-create                    Create a port connecting a server to a network
port-inspect                   Inspect the state of a port in DB and Ganeti
port-list                      List ports
port-remove                    Delete a port
floating-ip-create             Create a new floating IP
floating-ip-attach             Attach a floating IP to a server
floating-ip-detach             Detach a floating IP from a server
floating-ip-list               List floating IPs
floating-ip-remove             Delete a floating IP
queue-inspect                  Inspect the messages of a RabbitMQ queue
queue-retry                    Resend messages from Dead Letter queues to original exchanges
service-export-cyclades        Export Cyclades services and resources in JSON format
subnet-create                  Create a subnet
subnet-inspect                 Inspect a subnet in DB
subnet-list                    List subnets
subnet-modify                  Modify a subnet
reconcile-servers              Reconcile servers of Synnefo DB with state of Ganeti backend
reconcile-networks             Reconcile networks of Synnefo DB with state of Ganeti backend
reconcile-pools                Check consistency of pool resources
reconcile-commissions-cyclades Detect and resolve pending commissions to Quotaholder
reconcile-resources-cyclades   Reconcile resource usage of Astakos with Cyclades DB.
============================== ===========================


Astakos helper scripts
======================

Astakos includes two scripts to facilitate the installation procedure.
Running:

.. code-block:: console

   snf-component-register [<component_name>]

automates the registration of the standard Synnefo components (astakos,
cyclades, and pithos) in astakos database. It internally uses the script:

.. code-block:: console

   snf-service-export <component_name> <base_url>

which simulates the export of service and resource definitions of the
standard Synnefo components.


Pithos managing accounts
========================

Pithos provides a utility tool for managing accounts.
To run you just type:

.. code-block:: console

   # pithos-manage-accounts <command> [arguments]

This is the list of the available commands:

============================  ===========================
Name                          Description
============================  ===========================
delete                        Remove an account from the Pithos DB
export-quota                  Export account quota in a file
list                          List existing/dublicate accounts
merge                         Move an account contents in another account
set-container-quota           Set container quota for all or a specific account
============================  ===========================


The "kamaki" API client
=======================

To upload, register or modify an image you will need the **kamaki** tool.
Before proceeding make sure that it is configured properly. Verify that
*image.url*, *file.url*, *user.url* and *token* are set as needed:

.. code-block:: console

   $ kamaki config list

To change a setting use ``kamaki config set``:

.. code-block:: console

   $ kamaki config set cloud.default.url https://example.com/identity/v2.0
   $ kamaki config set cloud.default.token ...

To test that everything works, try authenticating the current account with
kamaki:

.. code-block:: console

  $ kamaki user authenticate

This will output user information.

Upload Image
------------

By convention, images are stored in a container called ``images``. Check if the
container exists, by listing all containers in your account:

.. code-block:: console

   $ kamaki file list /images

If the container ``images`` does not exist, create it:

.. code-block:: console

  $ kamaki container create images

You are now ready to upload an image to container ``images``. You can upload it
with a Pithos client, or use kamaki directly:

.. code-block:: console

   $ kamaki file upload ubuntu.iso /images

You can use any Pithos client to verify that the image was uploaded correctly,
or you can list the contents of the container with kamaki:

.. code-block:: console

  $ kamaki file list /images

The full Pithos URL for the previous example will be
``pithos://u53r-un1qu3-1d/images/ubuntu.iso`` where ``u53r-un1qu3-1d`` is the
unique user id (uuid).

Register Image
--------------

To register an image you will need to use the full or the relative Pithos URL.
To register as a public image the one from the previous example use:

.. code-block:: console

   $ kamaki image register --name=Ubuntu --location=/images/ubuntu.iso --public

The ``--public`` flag is important, if missing the registered image will not
be listed by ``kamaki image list``.

Use ``kamaki image register`` with no arguments to see a list of available
options. A more complete example would be the following:

.. code-block:: console

   $ kamaki image register --name Ubuntu --location /images/ubuntu.iso \
            --public --disk-format diskdump --property kernel=3.1.2

To verify that the image was registered successfully use:

.. code-block:: console

   $ kamaki image list --name-like ubuntu


Miscellaneous
=============

.. _branding:

Branding
--------

Since Synnefo v0.14, you are able to adapt the Astakos, Pithos and Cyclades Web
UI to your company’s visual identity. This is possible using the snf-branding
component, which is automatically installed on the nodes running the API
servers for Astakos, Pithos and Cyclades.

Configuration
~~~~~~~~~~~~~

This can be done by modifing the settings provided by the snf-branding component
to match your service identity. The settings for the snf-branding application
can be found inside the configuration file ``/etc/synnefo/15-snf-branding.conf``
on the nodes that have Astakos, Pithos and Cyclades installed.

By default, the global service name is "Synnefo" and the company name is
"GRNET". These names and their respective logos and URLs are used throughout
the Astakos, Pithos and Cyclades UI.

**Names and URLs:**

The first group of branding customization refers to the service's and company's
information.

You can overwrite the company and the service name and URL respectively by
uncommenting and setting the following:

.. code-block:: python

  # setting used in Astakos Dashboard/Projects pages
  BRANDING_SERVICE_NAME = 'My cloud'
  BRANDING_SERVICE_URL = 'http://www.mycloud.synnefo.org/'

  # settings used in Astakos, Pithos, Cyclades footer only if
  # BRANDING_SHOW_COPYRIGHT is set to True
  BRANDING_SHOW_COPYRIGHT = True
  BRANDING_COMPANY_NAME = 'Company LTD'
  BRANDING_COMPANY_URL = 'https://www.company-ltd.synnefo.org/'


**Copyright and footer options:**

By default, no Copyright message is shown in the UI footer. If you want to make
it visible in the footer of Astakos, Pithos and Cyclades UI, you can uncomment
and set to ``True`` the ``BRANDING_SHOW_COPYRIGHT`` setting:

.. code-block:: python

  #BRANDING_SHOW_COPYRIGHT = False

Copyright message defaults to 'Copyright (c) 2011-<current_year>
<BRANDING_COMPANY_NAME>.' but you can overwrite it to a completely custom one by
setting the following option:

.. code-block:: python

  BRANDING_COPYRIGHT_MESSAGE = 'Copyright (c) 2011-2013 GRNET'

If you want to include a custom message in the footer, you can uncomment and
set the ``BRANDING_FOOTER_EXTRA_MESSAGE`` setting. You can use html markup.
Your custom message will appear  above Copyright message at the Compute
templates and the Dashboard UI.

.. code-block:: python

  #BRANDING_FOOTER_EXTRA_MESSAGE = ''


**Images:**

The Astakos, Pithos and Cyclades Web UI has some logos and images.

The branding-related images are presented in  the following table:

===============  ============================  =========
Image            Name/extension  convention    Usage
===============  ============================  =========
Favicon          favicon.ico                   Favicon for all services
Dashboard logo   dashboard_logo.png            Visible in all Astakos UI pages
Compute logo     compute_logo.png              Visible in all Cyclades UI pages
Console logo     console_logo.png              Visible in the Cyclades Console Window
Storage logo     storage_logo.png              Visible in all Pithos UI pages
===============  ============================  =========

There are two methods  available for replacing all, or individual,
branding-related images:

1. Create a new directory inside ``/usr/share/synnefo/static/`` (e.g.
   ``mybranding``) and place there some or all of your images.

   If you want to replace all of your images, keep the name/extension
   conventions as indicated in the above table and change the
   ``BRANDING_IMAGE_MEDIA_URL`` setting accordingly:

   .. code-block:: python

      # using relative path
      BRANDING_IMAGE_MEDIA_URL= '/static/mybranding/images/'

      # or if you already host them in a separate domain (e.g. cdn)
      BRANDING_IMAGE_MEDIA_URL= 'https://cdn.synnefo.org/branding/images/'


   If you wish to replace individual images, **do not uncomment**
   ``BRANDING_IMAGE_MEDIA_URL``, but instead provide a relative path, pointing to
   the file inside your directory for each ``BRANDING_<image>_URL`` that you wish
   to replace.

2. Upload some or all of your images to a server and replace each
   ``BRANDING_<image>_URL`` with the absolute url of the image (i.e.
   ``BRANDING_DASHBOARD_URL = 'https://www.synnefo.com/images/my_dashboard.jpg'``).

   Note that the alternative text  for each image tag inside html documents is
   alt=“BRANDING_SERVICE_NAME {Dashboard, Compute. Console, Storage}” respectively.

.. note:: Retina optimized images:

   Synnefo UI is optimized for Retina displays. As far as images are concerned,
   `retina.js <http://retinajs.com/>`_ is used.

   Retina.js checks each image on a page to see if there is a high-resolution
   version of that image on your server. If a high-resolution variant exists,
   the script will swap in that image in-place.

   The script assumes you use  `Apple's prescribed high-resolution modifier (@2x)
   <http://developer.apple.com/library/ios/#documentation/2DDrawing/Conceptual/
   DrawingPrintingiOS/SupportingHiResScreensInViews/SupportingHiResScreensInViews
   .html#//apple_ref/doc/uid/TP40010156-CH15-SW1>`_ to denote high-resolution
   image variants on your server.

   For each of the images that you wish the script to  replace, you must have a
   high-resolution variant in the same folder  named correctly and it will be
   detected automatically. For example if your image is in <my_directory> and is
   named "my_image.jpg" the script will look in the same directory for an image
   named "my_image@2x.jpg".

   In case that you don’t want to use a high-resolution image, the
   normal-resolution image will be visible.

More branding
~~~~~~~~~~~~~

Although, it is not 100% branding-related, further verbal customization is
feasible.

**EMAILS**

The output of all email `*`.txt files will be already customized to contain your
company and service names but you can further alter their content if you feel it
best fits your needs.

In order to overwrite one or more email-templates you need to place your
modified <email-file>.txt files respecting the following structure:

  **/etc/synnefo/templates/**
      **im/**
          | activation_email.txt
          | email.txt
          | invitation.txt
          | switch_accounts_email.txt
          | welcome_email.txt
          **projects/**
              | project_approval_notification.txt
              | project_denial_notification.txt
              | project_membership_change_notification.txt
              | project_membership_enroll_notification.txt
              | project_membership_leave_request_notification.txt
              | project_membership_request_notification.txt
              | project_suspension_notification.txt
              | project_termination_notification.txt
      **registration/**
          | email_change_email.txt
          | password_email.txt

Feel free to omit any of the above files you do not wish to overwrite.

Below is a list of all emails sent by Synnefo to users along with a short
description and a link to their content:

* ``snf-astakos-app/astakos/im/templates/im/email.txt``
  Base email template. Contains a contact email and a “thank you” message.
  (`Link <https://code.grnet.gr/projects/synnefo/repository/revisions/master/changes/snf-astakos-app/astakos/im/templates/im/email.txt>`_)
* ``snf-astakos-app/astakos/im/templates/im/activation_email.txt`` Email sent to
  user that prompts  him/her to click on a link provided to activate the account.
  Extends “email.txt” (`Link <https://code.grnet.gr/projects/synnefo/repository/revisions/master/changes/snf-astakos-app/astakos/im/templates/im/activation_email.txt>`_)
* ``snf-astakos-app/astakos/im/templates/im/invitation.txt`` Email sent to an
  invited user. He/she has to click on a link provided to activate the account.
  Extends “email.txt” (`Link <https://code.grnet.gr/projects/synnefo/repository/revisions/master/changes/snf-astakos-app/astakos/im/templates/im/invitation.txt>`_)
* ``snf-astakos-app/astakos/im/templates/im/switch_accounts_email.txt`` Email
  sent to user upon his/her request to associate this email address with a
  shibboleth account. He/she has to click on a link provided to activate the
  association. Extends “email.txt” (`Link <https://code.grnet.gr/projects/synnefo/repository/revisions/master/changes/snf-astakos-app/astakos/im/templates/im/switch_accounts_email.txt>`_)
* ``snf-astakos-app/astakos/im/templates/im/welcome_email.txt`` Email sent to
  inform the user that his/ her account has been activated. Extends “email.txt”
  (`Link <https://code.grnet.gr/projects/synnefo/repository/revisions/master/changes/snf-astakos-app/astakos/im/templates/im/welcome_email.txt>`_)
* ``snf-astakos-app/astakos/im/templates/registration/email_change_email.txt``
  Email sent to user when he/she has requested new email address assignment. The
  user has to click on a link provided to validate this action. Extends
  “email.txt” (`Link <https://code.grnet.gr/projects/synnefo/repository/revisions/master/changes/snf-astakos-app/astakos/im/templates/registration/email_change_email.txt>`_)
* ``snf-astakos-app/astakos/im/templates/registration/password_email.txt`` Email
  sent for resetting password purpose. The user has to click on a link provided
  to validate this action. Extends “email.txt” (`Link <https://code.grnet.gr/projects/synnefo/repository/revisions/master/changes/snf-astakos-app/astakos/im/templates/registration/password_email.txt>`_)
* ``snf-astakos-app/astakos/im/templates/im/projects/project_approval_notification.txt``
  Informs  the project owner that his/her project has been approved. Extends
  “email.txt” (`Link <https://code.grnet.gr/projects/synnefo/repository/revisions/master/changes/snf-astakos-app/astakos/im/templates/im/projects/project_approval_notification.txt>`_)
* ``snf-astakos-app/astakos/im/templates/im/projects/project_denial_notification.txt``
  Informs the project owner that his/her  project application has been denied
  explaining the reasons. Extends “email.txt” (`Link <https://code.grnet.gr/projects/synnefo/repository/revisions/master/changes/snf-astakos-app/astakos/im/templates/im/projects/project_denial_notification.txt>`_)
* ``snf-astakos-app/astakos/im/templates/im/projects/project_membership_change_notification.txt``
  An email is sent to a user containing information about his project membership
  (whether he has been accepted, rejected or removed). Extends “email.txt” (`Link
  <https://code.grnet.gr/projects/synnefo/repository/revisions/master/changes/snf-astakos-app/astakos/im/templates/im/projects/project_membership_change_notification.txt>`_)
* ``snf-astakos-app/astakos/im/templates/im/projects/project_membership_enroll_notification.txt``
  Informs a user that he/she  has been enrolled to a project. Extends
  “email.txt” (`Link <https://code.grnet.gr/projects/synnefo/repository/revisions/master/changes/snf-astakos-app/astakos/im/templates/im/projects/project_membership_enroll_notification.txt>`_)
* ``snf-astakos-app/astakos/im/templates/im/projects/project_membership_leave_request_notification.txt``
  An email is sent to the project owner to make him aware of a  user having
  requested to leave his project. Extends “email.txt” (`Link <https://code.grnet.gr/projects/synnefo/repository/revisions/master/changes/snf-astakos-app/astakos/im/templates/im/projects/project_membership_leave_request_notification.txt>`_)
* ``snf-astakos-app/astakos/im/templates/im/projects/project_membership_request_notification.txt``
  An email is sent to the project owner to make him/her aware of a user having
  requested to join  his project. Extends “email.txt” (`Link <https://code.grnet.gr/projects/synnefo/repository/revisions/master/changes/snf-astakos-app/astakos/im/templates/im/projects/project_membership_request_notification.txt>`_)
* ``snf-astakos-app/astakos/im/templates/im/projects/project_suspension_notification.txt``
  An email is sent to the project owner to make him/her aware of his/her project
  having been suspended. Extends “email.txt” (`Link <https://code.grnet.gr/projects/synnefo/repository/revisions/master/changes/snf-astakos-app/astakos/im/templates/im/projects/project_suspension_notification.txt>`_)
* ``snf-astakos-app/astakos/im/templates/im/projects/project_termination_notification.txt``
  An email is sent to the project owner to make him/her aware of his/her project
  having been terminated. Extends “email.txt” (`Link <https://code.grnet.gr/projects/synnefo/repository/revisions/master/changes/snf-astakos-app/astakos/im/templates/im/projects/project_termination_notification.txt>`_)

.. warning:: Django templates language:

  If you choose to  overwrite these email templates, be mindful of the necessary
  information contained in django template variables that must not be omitted,
  such as the activation link for activating one’s account and many more.
  These variables are contained into {{}} inside the templates.

**Astakos landing page**

Astakos generates sensible default values used to display component-
specific details in several places across views (dashboard, cloudbar
etc.). One of these places is Astakos landing page where Synnefo components are
featured.

In case those values doesn't seem to suit your deployment, Astakos allows
you to override any of them using ``ASTAKOS_COMPONENTS_META`` setting
in your ``/etc/synnefo/20-snf-astakos-app-settings.conf`` configuration file.

So, for example if you want to add your own image for Astakos service and in the
same time hide Cyclades service from Astakos landing page you can
add the following line to your configuration file:

.. code-block:: python

  ASTAKOS_COMPONENTS_META = {
    'astakos': {
      'dashboard': {
        'icon': '<path-to-your-icon>'
      }
    },
    'cyclades': {
      'dashboard': {
        'show': False
      }
    }
  }

A complete list of available keys is shown below:

.. code-block:: python

  '<component-name>' = {
    'order': 1,
    'dashboard': {
      'order': 1,
      'show': True,
      'description': '<component-description>',
      'icon': '<component-icon-path>',
    },
    'cloudbar': {
      'show': True
    }
  }


**403, 404 and 500 pages**

Feel free to add your own 403 (HTTP Forbidden), 404 (Page not found) and
500 (server error) pages.
To override the default Synnefo error views, you must write and include any of
the files 403.html, 404.html and 500.html in your
**/etc/synnefo/templates/** directory.

Their content is up to you, but you may use as guides the default error pages
found in:

  **/synnefo/snf-webproject/synnefo/webproject/templates/**
    | 403.html
    | 404.html
    | 500.html



.. RabbitMQ

RabbitMQ Broker
---------------

Queue nodes run the RabbitMQ sofware, which provides AMQP functionality. To
guarantee high-availability, more than one Queue nodes should be deployed, each
of them belonging to the same `RabbitMQ cluster
<http://www.rabbitmq.com/clustering.html>`_. Synnefo uses the RabbitMQ
active/active `High Available Queues <http://www.rabbitmq.com/ha.html>`_ which
are mirrored between two nodes within a RabbitMQ cluster.

The RabbitMQ nodes that form the cluster, are declared to Synnefo through the
`AMQP_HOSTS` setting. Each time a Synnefo component needs to connect to
RabbitMQ, one of these nodes is chosen in a random way. The client that Synnefo
uses to connect to RabbitMQ, handles connection failures transparently and
tries to reconnect to a different node. As long as one of these nodes are up
and running, functionality of Synnefo should not be downgraded by the RabbitMQ
node failures.

All the queues that are being used are declared as durable, meaning that
messages are persistently stored to RabbitMQ, until they get successfully
processed by a client.

Currently, RabbitMQ is used by the following components:

* `snf-ganeti-eventd` and `snf-progress-monitor`:
  These components send messages concerning the status and progress of
  jobs in the Ganeti backend.
* `snf-dispatcher`: This daemon, consumes the messages that are sent from
  the above components, and updates the Cyclades DB accordingly.


Installation
~~~~~~~~~~~~

Please check the RabbitMQ documentation which covers extensively the
`installation of RabbitMQ server <http://www.rabbitmq.com/download.html>`_ and
the setup of a `RabbitMQ cluster <http://www.rabbitmq.com/clustering.html>`_.
Also, check out the `web management plugin
<http://www.rabbitmq.com/management.html>`_ that can be useful for managing and
monitoring RabbitMQ.

For a basic installation of RabbitMQ on two nodes (node1 and node2) you can do
the following:

On both nodes, install rabbitmq-server and create a Synnefo user:

.. code-block:: console

  $ apt-get install rabbitmq-server
  $ rabbitmqctl add_user synnefo "example_pass"
  $ rabbitmqctl set_permissions synnefo  ".*" ".*" ".*"

Also guarantee that both nodes share the same cookie, by running:

.. code-block:: console

  $ scp node1:/var/lib/rabbitmq/.erlang.cookie node2:/var/lib/rabbitmq/.erlang.cookie

and restart the nodes:

.. code-block:: console

  $ /etc/init.d/rabbitmq-server restart


To setup the RabbitMQ cluster run:

.. code-block:: console

  root@node2: rabbitmqctl stop_app
  root@node2: rabbitmqctl reset
  root@node2: rabbitmqctl cluster rabbit@node1 rabbit@node2
  root@node2: rabbitmqctl start_app

You can verify that the cluster is set up correctly by running:

.. code-block:: console

  root@node2: rabbitmqctl cluster_status


Logging
-------

Logging in Synnefo is using Python's logging module. The module is configured
using dictionary configuration, whose format is described here:

http://docs.python.org/release/2.7.1/library/logging.html#logging-config-dictschema

The logging configuration dictionary is defined in
``/etc/synnefo/10-snf-webproject-logging.conf``

The administrator can have logging control by modifying the ``LOGGING_SETUP``
dictionary, and defining subloggers with different handlers and log levels.

By default snf-manage will log any command that is being executed along with
its output under the directory ``LOG_DIR``/commands. The ``LOG_DIR`` directory
can be changed from the ``00-snf-common-admins.conf`` configuration file and
the whole snf-manage logging mechanism can be disabled by changing the
``LOGGER_EXCLUDE_COMMANDS`` setting to ".\*".


.. _scale-up:

Scaling up to multiple nodes
============================

Here we will describe how should a large scale Synnefo deployment look like. Make
sure you are familiar with Synnefo and Ganeti before proceeding with this section.
This means you should at least have already set up successfully a working Synnefo
deployment as described in the :ref:`Admin's Installation Guide
<quick-install-admin-guide>` and also read the Administrator's Guide until this
section.

Graph of a scale-out Synnefo deployment
---------------------------------------

Each box in the following graph corresponds to a distinct physical node:

.. image:: images/synnefo-arch2-roles.png
   :width: 100%
   :target: _images/synnefo-arch2-roles.png

The above graph is actually the same with the one at the beginning of this
:ref:`guide <admin-guide>`, with the only difference that here we show the
Synnefo roles of each physical node. These roles are described in the
following section.

.. _physical-node-roles:

Physical Node roles
-------------------

As appears in the previous graph, a scale-out Synnefo deployment consists of
multiple physical nodes that have the following roles:

* **WEBSERVER**: A web server running in front of gunicorn (e.g.: Apache, nginx)
* **ASTAKOS**: The Astakos application (gunicorn)
* **ASTAKOS_DB**: The Astakos database (postgresql)
* **PITHOS**: The Pithos application (gunicorn)
* **PITHOS_DB**: The Pithos database (postgresql)
* **CYCLADES**: The Cyclades application (gunicorn)
* **CYCLADES_DB**: The Cyclades database (postgresql)
* **MQ**: The message queue (RabbitMQ)
* **GANETI_MASTER**: The Ganeti master of a Ganeti cluster
* **GANETI_NODE** : A VM-capable Ganeti node of a Ganeti cluster

You will probably also have:

* **CMS**: The CMS used as a frotend portal for the Synnefo services
* **NS**: A nameserver serving all other Synnefo nodes and resolving Synnefo FQDNs
* **CLIENT**: A machine that runs the Synnefo clients (e.g.: kamaki, Web UI),
              most of the times, the end user's local machine

From this point we will also refer to the following groups of roles:

* **SYNNEFO**: [ **ASTAKOS**, **ASTAKOS_DB**, **PITHOS**, **PITHOS_DB**, **CYCLADES**, **CYCLADES_DB**, **MQ**, **CMS**]
* **G_BACKEND**: [**GANETI_MASTER**, **GANETI_NODE**]

Of course, when deploying Synnefo you can combine multiple of the above roles on a
single physical node, but if you are trying to scale out, the above separation
gives you significant advantages.

So, in the next section we will take a look on what components you will have to
install on each physical node depending on its Synnefo role. We assume the graph's
architecture.

Components for each role
------------------------

When deploying Synnefo in large scale, you need to install different Synnefo
or/and third party components on different physical nodes according to their
Synnefo role, as stated in the previous section.

Specifically:

Role **WEBSERVER**
    * Synnefo components: `None`
    * 3rd party components: Apache
Role **ASTAKOS**
    * Synnefo components: `snf-webproject`, `snf-astakos-app`
    * 3rd party components: Django, Gunicorn
Role **ASTAKOS_DB**
    * Synnefo components: `None`
    * 3rd party components: PostgreSQL
Role **PITHOS**
    * Synnefo components: `snf-webproject`, `snf-pithos-app`, `snf-pithos-webclient`
    * 3rd party components: Django, Gunicorn
Role **PITHOS_DB**
    * Synnefo components: `None`
    * 3rd party components: PostgreSQL
Role **CYCLADES**
    * Synnefo components: `snf-webproject`, `snf-cyclades-app`, `snf-vncauthproxy`
    * 3rd party components: Django Gunicorn
Role **CYCLADES_DB**
    * Synnefo components: `None`
    * 3rd party components: PostgreSQL
Role **MQ**
    * Synnefo components: `None`
    * 3rd party components: RabbitMQ
Role **GANETI_MASTER**
    * Synnefo components: `snf-cyclades-gtools`
    * 3rd party components: Ganeti
Role **GANETI_NODE**
    * Synnefo components: `snf-cyclades-gtools`, `snf-network`, `snf-image`, `nfdhcpd`
    * 3rd party components: Ganeti
Role **CMS**
    * Synnefo components: `snf-webproject`, `snf-cloudcms`
    * 3rd party components: Django, Gunicorn
Role **NS**
    * Synnefo components: `None`
    * 3rd party components: BIND
Role **CLIENT**
    * Synnefo components: `kamaki`, `snf-image-creator`
    * 3rd party components: `None`

Example scale out installation
------------------------------

In this section we describe an example of a medium scale installation which
combines multiple roles on 10 different physical nodes. We also provide a
:ref:`guide <i-synnefo>` to help with such an install.

We assume that we have the following 10 physical nodes with the corresponding
roles:

Node1:
    **WEBSERVER**, **ASTAKOS**
      Guide sections:
        * :ref:`apt <i-apt>`
        * :ref:`gunicorn <i-gunicorn>`
        * :ref:`apache <i-apache>`
        * :ref:`snf-webproject <i-webproject>`
        * :ref:`snf-astakos-app <i-astakos>`
Node2:
    **WEBSERVER**, **PITHOS**
      Guide sections:
        * :ref:`apt <i-apt>`
        * :ref:`gunicorn <i-gunicorn>`
        * :ref:`apache <i-apache>`
        * :ref:`snf-webproject <i-webproject>`
        * :ref:`snf-pithos-app <i-pithos>`
        * :ref:`snf-pithos-webclient <i-pithos>`
Node3:
    **WEBSERVER**, **CYCLADES**
      Guide sections:
        * :ref:`apt <i-apt>`
        * :ref:`gunicorn <i-gunicorn>`
        * :ref:`apache <i-apache>`
        * :ref:`snf-webproject <i-webproject>`
        * :ref:`snf-cyclades-app <i-cyclades>`
        * :ref:`snf-vncauthproxy <i-cyclades>`
Node4:
    **WEBSERVER**, **CMS**
      Guide sections:
        * :ref:`apt <i-apt>`
        * :ref:`gunicorn <i-gunicorn>`
        * :ref:`apache <i-apache>`
        * :ref:`snf-webproject <i-webproject>`
        * :ref:`snf-cloudcms <i-cms>`
Node5:
    **ASTAKOS_DB**, **PITHOS_DB**, **CYCLADES_DB**
      Guide sections:
        * :ref:`apt <i-apt>`
        * :ref:`postgresql <i-db>`
Node6:
    **MQ**
      Guide sections:
        * :ref:`apt <i-apt>`
        * :ref:`rabbitmq <i-mq>`
Node7:
    **GANETI_MASTER**, **GANETI_NODE**
      Guide sections:
        * :ref:`apt <i-apt>`
        * :ref:`general <i-backends>`
        * :ref:`ganeti <i-ganeti>`
        * :ref:`snf-cyclades-gtools <i-gtools>`
        * :ref:`snf-network <i-network>`
        * :ref:`snf-image <i-image>`
        * :ref:`nfdhcpd <i-network>`
Node8:
    **GANETI_NODE**
      Guide sections:
        * :ref:`apt <i-apt>`
        * :ref:`general <i-backends>`
        * :ref:`ganeti <i-ganeti>`
        * :ref:`snf-cyclades-gtools <i-gtools>`
        * :ref:`snf-network <i-network>`
        * :ref:`snf-image <i-image>`
        * :ref:`nfdhcpd <i-network>`
Node9:
    **GANETI_NODE**
      Guide sections:
        `Same as Node8`
Node10:
    **GANETI_NODE**
      Guide sections:
        `Same as Node8`

All sections: :ref:`Scale out Guide <i-synnefo>`


Regions, Zones and Clusters
===========================

Region
------

A Region is a single Synnefo installation, with
Compute/Network/Image/Volume/Object Store services. A Region is associated with
one set of Synnefo DBs (Astakos DB, Pithos DB and Cyclades DB). Every Region has a
distinct set of API endpoints, e.g.,
`https://cloud.example.com/cyclades/compute/v2.0`. Two Regions are most times
located geographically far from each other, e.g. "Europe", "US-East". A Region
comprises multiple Zones.

Zone
----

A Zone is a set of Ganeti clusters, in a potentially geographically distinct
location, e.g. "Athens", "Rome". All clusters have access to the same physical
networks, and are considered a single failure domain, e.g., they access the
network over the same router. A Zone comprises muliple Ganeti clusters.

Ganeti cluster
--------------

A Ganeti cluster is a set of Ganeti nodes (physical machines). One of the nodes
has the role of "Ganeti master". If this node goes down, another node may
undertake the master role. Ganeti nodes run Virtual Machines (VMs). VMs can live
migrate inside a Ganeti cluster. A Ganeti cluster comprises multiple physical
hardware nodes, most times geographically close to each other.

VM mobility
-----------

VMs may move across Regions, Zones, Ganeti clusters and physical nodes. Before we
describe how that's possible, we will describe the different kinds of moving,
providing the corresponding terminology:

Live migration
~~~~~~~~~~~~~~

The act of moving a running VM from physical node to physical node without any
impact on its operation. The VM continues to run on its new physical location,
completely unaffected, and without any service downtime or dropped connections.
Live migration typically requires shared storage and networking between the source
and destination nodes.

Live migration is issued by the administrator in the background and is transparent
to the VM user.

Failover
~~~~~~~~

The act of moving a VM from physical node to physical node by stopping it first on
the source node, then re-starting it on the destination node. There is short
service downtime, during the time the VM boots up, and client connections are
dropped.

Failover is issued by the administrator in the background and the VM user will
experience a reboot.

Snapshot Failover
~~~~~~~~~~~~~~~~~

The act of moving a VM from physical node to physical node via a point-in-time
snapshot. That is, stopping a VM on the source node, taking a snapshot, then
creating a new VM from that snapshot.

Snapshot failover is issued by the VM user and not the administrator.

Disaster Recovery
-----------------

In Synnefo terminology, Disaster Recovery is the process of sustaining a disaster
in one datacenter, and ensuring business continuity by performing live migration
or failover of running/existing VMs, or respawning VMs from previously made
snapshots. Based on the method used, this can work inside a single Ganeti cluster,
across Ganeti clusters in the same Zone, or across Zones.

Specifically:

Live migration is only supported inside a single Ganeti cluster. Ganeti supports
live migration between nodes in the same cluster with or without shared storage.
Live migration is done at the Ganeti level and is transparent to Synnefo.

Failover is supported inside a Ganeti cluster, across Ganeti clusters and across
Zones. Ganeti supports failover inside a Ganeti cluster with or without shared
storage, which poses minimum downtime for the VM. Failover inside the same Ganeti
cluster is done at the Ganeti level and is transparent to Synnefo.

Ganeti also provides tools for failing over VMs across different Ganeti clusters,
meaning that one can use them to failover VMs across Ganeti clusters of the same
Zone or across Ganeti clusters of different Zones, thus moving across Zones.
Failing over across different Ganeti clusters requires copying of data, resulting
in longer downtimes, depending on the geographical distance and network between
them. Failover across Ganeti clusters, either in the same or different Zones, is
not transparent to Synnefo and requires manual import of intances at Synnefo level
too, by the administrator.

Snapshot failover supports moving VMs across all domains. It is issued by the VM
user and is done at the Synnefo level without the need of running anything at the
Ganeti level or by the administrator.

In the future Synnefo will also support moving VMs across different Regions.


Upgrade Notes
=============

.. toctree::
   :maxdepth: 1

   v0.12 -> v0.13 <upgrade/upgrade-0.13>
   v0.13 -> v0.14 <upgrade/upgrade-0.14>
   v0.14 -> v0.14.2 <upgrade/upgrade-0.14.2>
   v0.14.5 -> v0.14.6 <upgrade/upgrade-0.14.6>
   v0.14.7 -> v0.14.8 <upgrade/upgrade-0.14.8>
   v0.14.9 -> v0.14.10 <upgrade/upgrade-0.14.10>
   v0.14 -> v0.15 <upgrade/upgrade-0.15>
   v0.15 -> v0.16 <upgrade/upgrade-0.16>


Changelog, NEWS
===============


* v0.15 :ref:`Changelog <Changelog-0.15>`, :ref:`NEWS <NEWS-0.15>`
* v0.14.10 :ref:`Changelog <Changelog-0.14.10>`, :ref:`NEWS <NEWS-0.14.10>`
* v0.14.9 :ref:`Changelog <Changelog-0.14.9>`, :ref:`NEWS <NEWS-0.14.9>`
* v0.14.8 :ref:`Changelog <Changelog-0.14.8>`, :ref:`NEWS <NEWS-0.14.8>`
* v0.14.7 :ref:`Changelog <Changelog-0.14.7>`, :ref:`NEWS <NEWS-0.14.7>`
* v0.14.6 :ref:`Changelog <Changelog-0.14.6>`, :ref:`NEWS <NEWS-0.14.6>`
* v0.14.5 :ref:`Changelog <Changelog-0.14.5>`, :ref:`NEWS <NEWS-0.14.5>`
* v0.14.4 :ref:`Changelog <Changelog-0.14.4>`, :ref:`NEWS <NEWS-0.14.4>`
* v0.14.3 :ref:`Changelog <Changelog-0.14.3>`, :ref:`NEWS <NEWS-0.14.3>`
* v0.14.2 :ref:`Changelog <Changelog-0.14.2>`, :ref:`NEWS <NEWS-0.14.2>`
* v0.14 :ref:`Changelog <Changelog-0.14>`, :ref:`NEWS <NEWS-0.14>`
* v0.13 :ref:`Changelog <Changelog-0.13>`, :ref:`NEWS <NEWS-0.13>`
