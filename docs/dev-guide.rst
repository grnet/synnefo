.. _dev-guide:

Synnefo Developer's Guide
^^^^^^^^^^^^^^^^^^^^^^^^^

This is the complete Synnefo Developer's Guide.

Environment set up
==================

First of all you have to set up a developing environment for Synnefo.

**1. Create a new VM**

It has been tested on Debian Wheezy. It is expected to work with other
releases (e.g., Squeeze) too, as long as they are supported by
``snf-deploy``.

**2. Build your own Synnefo installation**

Follow the instructions `here <http://www.synnefo.org/docs/synnefo/latest/quick-install-guide.html>`_
to build Synnefo on a single node using ``snf-deploy``.

**3. Install GitPython**

.. code-block:: console

   # pip install gitpython

**4. Install devflow**

Devflow is a tool to manage versions, helps implement the git flow development process,
and builds Python and Debian packages. You will need it to create your code's version.

.. code-block:: console

   # pip install devflow

**5. Get Synnefo code**

First you need to install git

.. code-block:: console

   # apt-get install git

And now get the Synnefo code from the official Synnefo repository

.. code-block:: console

   # su some_regular_user
   $ git clone https://code.grnet.gr/git/synnefo

Make sure you clone the repository as a regular user. Otherwise you will
have problems with file permissions when deploying.

**6. Code and deploy**

1. Configure the version

.. code-block:: console

   $ devflow-update-version

2. Code
3. In every component you change, run as root

.. code-block:: console

   # python setup.py develop -N

This does not automatically install dependencies, in order to avoid
confusion with Synnefo packages installed by ``snf-deploy``. External
dependencies have already been installed by ``snf-deploy``; if you introduce
a new dependency, you will have to explicitly install it.

4. You will need to restart the server with

.. code-block:: console

   # service gunicorn restart

5. If your changes affected ``snf-dispatcher`` (from package
   ``snf-cyclades-app``) or ``snf-ganeti-eventd`` (from
   ``snf-cyclades-gtools``) you will need to restart these daemons, too.
   Since step 3 installed the former under ``/usr/local/``, you need to
   make sure that the correct version is evoked. You can override the
   version installed by ``snf-deploy`` with

.. code-block:: console

   # ln -sf /usr/local/bin/snf-dispatcher /usr/bin/snf-dispatcher

and then restart the daemons

.. code-block:: console

   # service snf-dispatcher restart
   # service snf-ganeti-eventd restart

6. Refresh the web page and see your changes
