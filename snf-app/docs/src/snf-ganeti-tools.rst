.. _snf-ganeti-tools:

Component snf-ganeti-tools
==========================

synnefo component :ref:`snf-ganeti-tools <snf-ganeti-tools>` is a set of
tools that need to be installed on all Ganeti nodes:

    * :ref:`event daemon <eventd>`
    * :ref:`hook <hook>`
    * :ref:`progress-monitor <progress_monitor>`

.. _eventd:

Event daemon
------------

synnefo component :ref:`snf-ganeti-tools <snf-ganeti-tools>` includes
``snf-ganeti-eventd``, the synnefo-specific Ganeti event daemon.
It monitors the Ganeti job queue and produces notifications to the rest of
the synnefo infrastructure over AMQP whenever a Ganeti job makes progress.

.. todo:: Document the event daemon, assemble things from other sources.

.. _hook:

Hook
----

synnefo component :ref:`snf-ganeti-tools <snf-ganeti-tools>` defines
a synnefo-specific hook, running inside Ganeti.

.. _progress_monitor:

Progress monitor
----------------

A small Python tool to monitor the progress of image deployment.

.. todo:: Document the synnefo-specific progress monitor.

Package source
**************

The source for component :ref:`snf-ganeti-tools <snf-ganeti-tools>`
lives under ``snf-ganeti-tools/`` at ``git://code.grnet.gr/git/synnefo``,
also accessible at
`code.grnet.gr <https://code.grnet.gr/projects/synnefo/repository/revisions/master/show/snf-ganeti-tools>`_.

Package installation
********************

.. todo:: kpap: verify instructions for installation from source.

Use ``pip`` to install the latest version of the package from source,
or request a specific version as ``snf-ganeti-tools==x.y.z``.

.. code-block:: bash

   pip install snf-ganeti-tools -f https://code.grnet.gr/projects/synnefo/files

On Debian Squeeze, install the ``snf-ganeti-tools`` Debian package.

Package configuration
*********************

.. note:: The Debian package does the following configuration steps
   automatically, see ``/etc/default/snf-ganeti-eventd``.

Event daemon
------------

Make sure the event daemon starts automatically on system boot.
Initscript ``conf/init.d/snf-ganeti-eventd`` is provided for your convenience.

Hook
----
The hook needs to be enabled for phases ``post-{add,modify,reboot,start,stop}``
by *symlinking* in
``/etc/ganeti/hooks/instance-{add,modify,reboot,start,stop}-post.d`` 
on :ref:`GANETI-MASTER <GANETI_MASTER>`, e.g.:

.. code-block:: bash

    root@ganeti-master:/etc/ganeti/hooks/instance-start-post.d# ls -l
    lrwxrwxrwx 1 root root 45 May   3 13:45 00-snf-ganeti-hook -> /home/devel/synnefo/snf-ganeti-hook/snf-ganeti-hook.py

.. todo:: fix the actual location of the link target above.

.. note::
    The link name may only contain "upper and lower case, digits,
    underscores and hyphens. In other words, the regexp ^[a-zA-Z0-9\_-]+$."

.. seealso::
   `Ganeti customisation using hooks <http://docs.ganeti.org/ganeti/master/html/hooks.html?highlight=hooks#naming>`_

Package settings
****************

Component :ref:`snf-ganeti-tools <snf-ganeti-tools>` requires the following
settings, as managed by :ref:`snf-common <snf-common>`:

.. literalinclude:: ../../../snf-ganeti-tools/synnefo/settings.py

.. todo:: make sure the settings are included properly.
