.. _snf-webproject:

Component snf-webproject
------------------------

synnefo component :ref:`snf-webproject <snf-webproject>` defines
a Django project in which the various other synnefo components
(:ref:`snf-asterias-app <snf-asterias-app>`,
:ref:`snf-pithos-app <snf-pithos-app>`, etc.) may run.

It provides a standard mechanism for every synnefo software component to modify
the list of Django apps to be executed inside the project (``INSTALLED_APPS``),
modify the list of middleware classes (``MIDDLEWARE_CLASSES``) and add its own
URL patterns.

.. todo:: Document snf-webproject facilities for developers

Package installation
--------------------

.. todo:: kpap: verify instructions for installation from source.

Use ``pip`` to install the latest version of the package from source,
or request a specific version as ``snf-webproject==x.y.z``.

.. code-block:: console

   pip install snf-webproject -f https://code.grnet.gr/projects/synnefo/files

On Debian Squeeze, install the ``snf-webproject`` Debian package.

Package configuration
---------------------

Web server configuration
************************

You need to configure your webserver to serve static files and relay
requests to :ref:`snf-webproject <snf-webproject>`.

Static files
````````````
* Choose an appropriate path (e.g. :file:`/var/lib/synnefo/static/`) from which
  your web server will serve all static files (js/css) required by the synnefo
  web frontend to run.
* Change the ``MEDIA_ROOT`` value in your settings (see :ref:`snf-common
  <snf-common>`) to point to that directory.
* Create symlinks to the static files of all synnefo webapp components
  inside the chosen directory, by running:

.. code-block:: console

    $ snf-manage link_static

.. todo:: perhaps include an ``snf-manage copy_static`` command?
* Configure your webserver to serve ``/static`` from the directory
  set in the ``MEDIA_ROOT`` setting.

.. todo:: Make the location of static files configurable. This has already
   been done for the UI, see ``UI_MEDIA_URL``.

Apache
``````

.. todo:: document Apache configuration

nginx
`````
This section describes a sample nginx configuration which uses FastCGI
to relay requests to synnefo.

First, use a distribution-specific mechanism (e.g., APT) to install nginx:

.. code-block:: console

   # apt-get install nginx

Then activate the following nginx configuration file by placing it under
:file:`/etc/nginx/sites-available` and symlinking under
:file:`/etc/nginx/sites-enabled`:

.. literalinclude:: ../_static/synnefo.nginx.conf

.. todo:: fix the location of the configuration file

`download <../_static/synnefo.nginx.conf>`_

Once nginx is configured, run the FastCGI server to receive incoming requests
from nginx. This requires installation of package ``flup``:

.. code-block:: console

    # apt-get install flup
    $ snf-manage runfcgi host=127.0.0.1 port=8015

For developers
--------------

.. todo:: kpap: describe the functions exported to Synnefo components for
   extending ``INSTALLED_APPS``, ``MIDDLEWARE_CLASSES`` and URL patterns.

