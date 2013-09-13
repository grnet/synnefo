.. _snf-common:

Component snf-common
--------------------

synnefo component :ref:`snf-common <snf-common>` defines a mechanism for
handling configuration settings, shared among all synnefo components. It also
defines default values for a number of common settings.

The final values of synnefo settings result from applying custom admin-defined
modifications to the default values specified by the various components.
:ref:`snf-common <snf-common>` provides a mechanism for discovering default
settings, which it then amends with user-provided configuration to provide the
final ``settings`` object.

Default settings
    Component ``snf-common`` provides a number of defaults in Python module
    ``synnefo.common.settings``. Every other component may extend the
    ``synnefo`` namespace package and provide an ``extend_settings()`` entry
    point in group ``synnefo.settings.FIXME``. The common settings initialization
    code calls all such endpoints one by one, to assemble the defaults.
User settings
    The administrator can modify any setting at will, using ``*.conf`` files
    under ``$SYNNEFO_SETTINGS_DIR``, which defaults to ``/etc/synnefo``.
    Code in `snf-common` executes all ``*.conf`` files in lexicographic
    order, as standard Python code, after assembling the set of defaults.

synnefo settings are usable as Django settings, when in a Django
context, or as a standard Python module when not using Django. This avoids
an unecessary dependendy on Django.

To use synnefo settings with Django, have ``$DJANGO_SETTINGS_MODULE`` point
to the ``synnefo.settings`` module

.. code-block:: console

    $ export DJANGO_SETTINGS_MODULE=synnefo.settings

then import Django settings as usual:

.. code-block:: python

    from django.conf import settings

When not in a Django context, import the ``synnefo.settings`` module directly:

.. code-block:: python

    from synnefo import settings

In both cases, assembly of default settings and execution of
``$SYNNEFO_SETTINGS_DIR/*.conf`` happens in the same way.

Package settings
----------------

Component :ref:`snf-sommon <snf-common>` requires the following
settings:

.. literalinclude:: ../synnefo/settings/default/admins.py
    :lines: 4-
