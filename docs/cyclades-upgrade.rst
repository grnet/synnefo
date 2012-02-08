Upgrade
=======

This file documents the upgrade to newer versions of the Synnefo software.
For more information, please see deployment guide.


v0.7.4 -> v0.8
--------------

Synnefo is now distributed packaged in python/debian packages. You should
consider the following when migrating from projects previously deployed from
source:
    
    * To keep consistency with future changes, change all ``python manage.py``
      calls to refer to the shipped ``snf-manage`` console script.
      This includes automation scripts, service scripts etc.

      Same applies for calls to ``dispatcher.py``, ``snf-tools/admin.py``,
      ``snf-tools/burnin.py`` and ``snf-tools/cloud.py`` which are replaced
      by ``snf-dispatcher``, ``snf-admin``, ``snf-burnin`` and ``snf-cloud``,
      respectively.

    * Copy custom settings files located in project's ``settings.d`` directory
      to ``/etc/synnefo/`` directory.

    * Migrate location from which :ref:`static files <static-files>` are served from.

.. warning::
   
   Synnefo settings have been refactored as part of the
   :ref:`snf-common <snf-common>` component. File locations may be inaccurate
   and the list of changed settings incomplete.  Please consult the actual
   files installed under ``/etc/synnefo`` as the authoritative source for new
   settings.

NEW APPS
    * The ``synnefo.ui.userdata`` application has been added in
      :file:`settings.d/00-apps.conf`. Application urls appended in
      :file:`ui/urls.py`.
      If no custom ``ROOT_URLCONF`` module is used, no url change is needed.
    * The new app has migrations defined.
      Use ``snf-manage migrate`` to migrate *all* apps.

NEW/UPDATED SETTINGS
    * ``BYPASS_AUTHENTICATION_TOKEN_SECRET`` replaces ``BYPASS_AUTHENTICATION_TOKEN``
      in :file:`settings/common/aai.py`.
    * New config file :file:`31-userdata.conf`, containing userdata app settings
    * ``USERDATA_SSH_KEY_LENGTH`` in :file:`31-userdata.conf`:
      Key length in bits for generated ssh keys
    * ``USERDATA_SSH_KEY_EXPONENT`` in :file:`31-userdata.conf`:
      Generated SSH key exponent
    * ``USERDATA_MAX_SSH_KEYS_PER_USER`` in :file:`31-userdata.conf`:
      Maximum number of ssh keys a user is allowed to have
    * ``UI_SUPPORT_SSH_OS_LIST``, in :file:`30-ui.conf`:
      A list of os names that support ssh public key assignment
    * ``UI_OS_DEFAULT_USER_MAP``, in :file:`30-ui.conf`:
      OS/username map to identify default user name for a specific os
    * ``VM_CREATE_NAME_TPL``, in :file:`30-ui.conf`:
      Template to be used for suggesting the user a default name for newly
      created VMs. String {0} gets replaced by the value of metadata key "os"
      for the Image.
    * ``UI_FLAVORS_DISK_TEMPLATES_INFO`` added in :file:`30-ui.conf`:
      Name/description metadata for the available flavor disk templates
    * ``VM_CREATE_SUGGESTED_FLAVORS`` in :file:`30-ui.conf`:
      Updated flavor data to include disk_template value.
    * ``GANETI_DISK_TEMPLATES`` and ``DEFAULT_GANETI_DISK_TEMPLATE`` in :file:`20-api.conf`:
      The list of disk templates supported by the Ganeti backend.
      The default template to be used when migrating Flavors with no value for
      disk_template (i.e., 'drbd').
    * ``UI_COMPUTE_URL``, ``UI_GLANCE_URL`` in ui app:
      Configurable API endpoints
    * ``UI_ENABLE_GLANCE`` in ui app:
      Whether or not UI should retrieve images from the Glance API endpoint
      set in ``UI_GLANCE_API_URL``. If setting is set to False, ui will request
      images using calls to the Cyclades API.
UI
    * ``synnefo.ui.userdata`` application has been added in ``INSTALLED_APPS``.
      Database migration is needed for the creation of application db tables.

API
    * A new ``disk_template`` attribute has been added to Flavors.
      ``GANETI_DISK_TEMPLATES`` and ``DEFAULT_GANETI_DISK_TEMPLATE`` have been
      added in :file:`20-api.conf` to control its value. A database migration is
      needed.

PLANKTON
    Plankton is a new image service that has been added as a separate app. The
    images are stored in backend of Pithos and thus it must be configured to
    access the DB and directory that Pithos uses to store its data. These
    settings are defined in the new plankton.py file in settings.
    
    Plankton stores and looks for images in the Pithos container named
    ``PITHOS_IMAGE_CONTAINER``.
    
    There is a Pithos account that is reserved for system images. This account
    is defined in ``SYSTEM_IMAGES_OWNER``.

ADMIN TOOLS
    * A new ``--disk-template`` flag has been added to snf-admin to choose a
      disk template when creating flavors. Similarly, ``disk_template`` support
      in flavors has beed added to the admin web interface.


v0.7.3 -> v0.7.4
----------------

OKEANOS INTRO
    * News section added. News content can be remotely retrieved using
      OKEANOS_NEWS_CONTENT_URL settings option.


v0.6.2 -> v0.7
--------------

HTML TEMPLATES
    * Included a generic service unavailable template based on
      generic_info_tpl.html, as ui/static/service_unavailable.html.

NEW DEPENDENCIES
    * python-unittest2, python-paramiko needed by the new integration
      test suite snf-tools/burnin. Paramiko shipped with Squeeze uses
      broken RandomPool, produces warnings, see #576697.
    * snf-image must be installed on all Ganeti hosts, see README.deploy,
      Step 13.

COMPONENTS
    * snf-admin has been updated with new functionality, be sure to upgrade any
      locally installed versions.
    * snf-image replaces snf-ganeti-instance-image as the Ganeti OS provider
      used by Synnefo, and can live alongside snf-ganeti-instance-image.
      Once snf-image has been deployed on all Ganeti nodes, be sure to modify
      the value of settings.d/10-backend.conf:GANETI_CREATEINSTANCE_KWARGS
      to use 'snf-image+default'.

UI STATIC FILES
    * A major reorganization of static files has been commited. All ui and
      invitations static files has been moved in their own separate directory
      (ui/static/snf, ui/static/invitations).
    * UI static files base url is now configurable via UI_MEDIA_URL.
    * A symlink named after the current version of the ui application has been
      committed in ui/static directory. The symlink will get updated after each
      version upgrade to allow us provide unique urls of static files between
      after each upgrade, see #1460.

NEW/UPDATED SETTINGS
    * EMAIL_SUBJECT_PREFIX:
      Prepended to automated emails, set to someting that uniquely identifies
      the deployment.
    * MAX_PERSONALITY and MAX_PERSONALITY_SIZE in 20-api.conf:
      Maximum number of files to be injected in newly created servers,
      maximum total size of encoded file contents.
    * Renamed SUGGESTED_FLAVORS to VM_CREATE_SUGGESTED_FLAVORS in 30-ui.conf
    * VM_CREATE_SUGGESTED_ROLES in 30-ui.conf:
      A list of suggested vm roles to display to user on create wizard.
    * UI_DELAY_ON_BLUR in 30-ui.conf:
      Whether to increase the intervals of recurrent requests (networks/vms 
      update) if window loses its focus.
    * UI_BLUR_DELAY in 30-ui.conf:
      The value of update intervals if window loses its focus.
      Considered only if `UI_DELAY_ON_BLUR` is set to True.
    * UI_UPDATE_HIDDEN_VIEWS in 30-ui.conf:
      Whether not visible vm views will update their content if vm changes.
    * UI_SKIP_TIMEOUTS in 30-ui.conf:
      After how many timeouts of reccurent ajax requests to display the timeout
      error overlay.
    * UI_HANDLE_WINDOW_EXCEPTIONS in 30-ui.conf:
      Whether UI should display error overlay for all Javascript exceptions.
    * UI_MEDIA_URL in 30-ui.conf:
      Base url for ui static files, 
      defaults to MEDIA_URL + 'snf-<latest_ui_version>/'.
    * MEDIA_URL changed in 00-site.conf:
      Changed to '/static/' since it is now used in ui app.
    * TEMPLATE_CONTEXT_PROCESSORS changed in 00-apps.conf:
      added 'django.core.context_processors.media' to allow access of MEDIA_URL
      in template files.
    * GANETI_CREATEINSTANCE_KWARGS in 10-backend.conf:
      Must be updated to use snf-image as the Ganeti OS provider.
      
    
DB MIGRATION
    * Uniqueness constraints have been added to the metadata models.
      A database migration is needed.

LOGGING
    * A new logging mechanism has been implemeted. Please see 00-logging.conf
      under settings.d/ and read the relevant section in README.admin for more
      info.


v0.6.1 -> v0.6.2
----------------

ADMIN INTERFACE
    * The models were changed so that Flavors and SynnefoUsers now have
      a deleted state. The admin tools were updated so that models are
      now marked as deleted instead of actually being deleted from the DB.
      A database migration is needed.

COMPONENTS
    * Only the Django webapp is affected, must restart the logic dispatcher
      due to DB migration taking place.


v0.5.5 -> v0.6
--------------

ADMIN INTERFACE
    * A new Web-based admin interface is available under /admin.
      It is accessible by users of type 'ADMIN' in the DB, with
      their authentication token. "snf-admin user modify" may be used
      to change the type of a specific user.

RECONCILIATION
    * Implemented new reconciliation management command, please see
      ./manage.py reconcile --help and README.admin for more info.
      Recommended to run ./manage.py reconcile --detect-all periodically,
      via cron.

GANETI-INSTANCE-IMAGE
    * A new version of ganeti-instance-image is required (v0.5.1-1-snf1).
      The new version is available for download as a debian package:
      https://code.grnet.gr/projects/gnt-instance-image/files

COMPONENTS
    * snf-cyclades-gtools must be rebuilt, see snf-cyclades-gtools/debian/
      for Debian packaging.

NEW SETTINGS
    * 30-ui.conf:SUGGESTED_FLAVORS
    * 30-ui.conf:VM_IMAGE_COMMON_METADATA


v0.5.4 -> v0.5.5
----------------

LOGGING
    * Changed the default logging settings for the dispatcher to also log
      to /var/log/synnefo/dispatcher.log, redirecting stderr and stdout there

QUEUES
    * Changed default routing key naming for queues. Queues must be redeclared.
      The suggested upgrade path is to delete ALL (even obsolete) existing
      queues and restart the dispatcher. To do so, download amqp-utils from

          https://github.com/dougbarth/amqp-utils

      and run the amqp-deleteq tool for each declared queue. Alternatively,
      amqp-utils can be installed with: sudo gem install amqp-utils.

UI
    * Feedback form now uses django native send_mail for sending emails.
      Proper django settings should be set for feedback mails to work
      (https://docs.djangoproject.com/en/dev/topics/email/)

COMPONENTS
    * snf-cyclades-gtools must be rebuilt, see snf-cyclades-gtools/debian/
      for Debian packaging.


v0.5.3 -> v0.5.4
----------------

REPOSITORY
    * Split Synnefo Ganeti tools to snf-cyclades-gtools, with Debian packaging

REMOVED APPS
    * The ganeti/ app has been removed from the Django project completely.
      Any explicit references to it in Django settings must be removed.

DJANGO SETTINGS
    * snf-cyclades-gtools is configured independently from Django,
      need to add proper /etc/synnefo/settings.conf
    * Removed 15-queues.conf: fix_amqp_settings (no need to call it anywhere)
    * Removed settings.d/98-ganeti-* due to split of snf-cyclades-gtools
    * ~okeanos intro: OKEANOS_VIDEO_URL: Changed from string to dict
    * ~okeanos intro: OKEANOS_VIDEO_POSTER_IMAGE_URL: New setting
    * ~okeanos intro: OKEANOS_VIDEO_FLOWPLAYER_URL: New setting

DB MIGRATIONS
    * 0018_auto__add_field_virtualmachine_buildpercentage

PACKAGING
    * Split Synnefo Ganeti tools to separate snf-cyclades-gtools Debian package

NEW DEPENDENCIES
    * python-prctl: Needed by the snf-progress-monitor,
      specified as a dependency of the snf-cyclades-gtools Debian package.

EXTERNAL COMPONENTS
    * Ganeti Instance Image must be upgraded to support progress monitoring,
      please see README.deploy.


v0.5.2 -> v0.5.3
----------------

NEW SETTINGS
    * 30-ui.conf:LOGOUT_URL
    * 00-admins.conf:DEFAULT_FROM_EMAIL
    * 90-okeanos.conf.sample:LOGOUT_URL

REMOVED SETTINGS
    * 00-admins.conf:SYSTEM_EMAIL_ADDR
    * 90-okeanos.conf.sample:APP_INSTALL_URL


v0.5.1 -> v0.5.2
----------------

NEW SETTINGS
    * 10-backend.py:GANETI_CREATEINSTANCE_KWARGS

REMOVED SETTINGS
    * 10-backend.conf:GANETI_OS_PROVIDER
    * 20-api.conf:GANETI_DISK_TEMPLATE

BACKEND CHANGES
    * Need to patch Ganeti, file:
      lib/python2.6/site-packages/ganeti/rapi/rlib2.py
      to honor the wait_for_sync flag, see Synnefo #835.
      Patch provided under contrib/patches/ganeti-rlib2.py-v0.5.2

