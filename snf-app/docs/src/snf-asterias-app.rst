.. _snf-asterias-app:

Component snf-asterias-app
==========================

synnefo component :ref:`snf-asterias-app <snf-asterias-app>` defines the main
web application for asterias, as a set of Django applications.

Package installation
--------------------

.. todo:: kpap: verify instructions for installation from source.

Use ``pip`` to install the latest version of the package from source,
or request a specific version as ``snf-asterias-app==x.y.z``.

.. code-block:: console

   $ pip install snf-asterias-app -f https://code.grnet.gr/projects/synnefo/files

On Debian Squeeze, install the ``snf-asterias-app`` Debian package.

Package configuration
---------------------

.. todo:: The Debian package does the following configuration steps
   automatically, see ``/etc/default/snf-ganeti-eventd``.

Event daemon
************

Make sure the event daemon starts automatically on system boot.
Initscript ``conf/init.d/snf-ganeti-eventd`` is provided for your convenience.

Hook
****
The hook needs to be enabled for phases ``post-{add,modify,reboot,start,stop}``
by *symlinking* in
``/etc/ganeti/hooks/instance-{add,modify,reboot,start,stop}-post.d`` 
on :ref:`GANETI-MASTER <GANETI_MASTER>`, e.g.:

.. code-block:: console

    root@ganeti-master:/etc/ganeti/hooks/instance-start-post.d# ls -l
    lrwxrwxrwx 1 root root 45 May   3 13:45 00-snf-ganeti-hook -> /home/devel/synnefo/snf-ganeti-hook/snf-ganeti-hook.py

.. todo:: fix the actual location of the link target above.

.. note::
    The link name may only contain "upper and lower case, digits,
    underscores and hyphens. In other words, the regexp ^[a-zA-Z0-9\_-]+$."

.. seealso::
   `Ganeti customisation using hooks <http://docs.ganeti.org/ganeti/master/html/hooks.html?highlight=hooks#naming>`_

Package settings
----------------

Component :ref:`snf-asterias-app <snf-asterias-app>` requires the following
settings, as managed by :ref:`snf-common <snf-common>`:

.. literalinclude:: ../../../snf-app/synnefo/app_settings/default/*.py

.. todo:: make sure the settings are included properly above this point.
