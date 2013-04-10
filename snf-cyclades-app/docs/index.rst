.. _snf-cyclades-app:

Component snf-cyclades-app
==========================

synnefo component :ref:`snf-cyclades-app <snf-cyclades-app>` defines
the web application for cyclades. It includes the following:

    * A set of Django applications that define among others:
        * web UI
        * API implementation
        * business logic layer
        * admin web UI
    * :ref:`snf-dispatcher <snf-dispatcher>`, the logic dispatcher

.. todo:: make this section more complete.

.. _snf-dispatcher:

snf-dispatcher
--------------

The logic dispatcher provides the context to run the business logic layer of
:ref:`cyclades <snf-cyclades>`. It must run on :ref:`LOGIC <LOGIC_NODE>` nodes.

The dispatcher retrieves messages from the queue, over AMQP, and calls the
appropriate handler function, based on the type of the message.

.. _snf-admin:

snf-admin
---------

command :command:`snf-admin` provides the command-line admin interface
for :ref:`cyclades <snf-cyclades>`.

Package installation
--------------------

.. todo:: kpap: verify instructions for installation from source.

Use ``pip`` to install the latest version of the package from source,
or request a specific version as ``snf-cyclades-app==x.y.z``.

.. code-block:: console

   $ pip install snf-cyclades-app -f https://docs.dev.grnet.gr/pypi

On Debian Squeeze, install the ``snf-cyclades-app`` Debian package.

Package configuration
---------------------

Web application
***************

Please see the configuration section of :ref:`snf-webproject <snf-webproject>`
on how to serve :ref:`snf-cyclades-app <snf-cyclades-app>` as part of a
Django project.

snf-dispatcher
**************

.. note:: 
    The Debian package configures the init script for
    ``snf-dispatcher`` automatically, see ``/etc/default/snf-dispatcher``.

.. todo:: package an initscript for :command:`snf-dispatcher`

Make sure the logic dispatcher starts automatically on system boot of
:ref:`LOGIC <LOGIC_NODE>` nodes. Initscript ``conf/init.d/snf-dispatcher``
is provided for your convenience.

You may also start the dispatcher by hand:

.. code-block:: console

  $ snf-dispatcher

The dispatcher should run in at least 2 instances to ensure high
(actually, increased) availability.

Package settings
----------------

Component :ref:`snf-cyclades-app <snf-cyclades-app>` requires the following
settings, as managed by :ref:`snf-common <snf-common>`:

.. literalinclude:: ../synnefo/app_settings/default/api.py
    :lines: 4-
.. literalinclude:: ../synnefo/app_settings/default/logging.py
    :lines: 4-
.. literalinclude:: ../synnefo/app_settings/default/backend.py
    :lines: 4-
.. literalinclude:: ../synnefo/app_settings/default/plankton.py
    :lines: 4-
.. literalinclude:: ../synnefo/app_settings/default/queues.py
    :lines: 4-
.. literalinclude:: ../synnefo/app_settings/default/ui.py
    :lines: 4-
.. literalinclude:: ../synnefo/app_settings/default/userdata.py
    :lines: 4-

.. todo:: make sure the file headers are included properly in documentation.
          If not change the :lines setting accordingly.
