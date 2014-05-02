.. _dev-guide:

Synnefo Developer's Guide
^^^^^^^^^^^^^^^^^^^^^^^^^

The suggested method of setting up an environment for development purposes is
first to install Synnefo on a Debian Wheezy system and then to use Python's
`development mode
<http://www.ewencp.org/blog/a-brief-introduction-to-packaging-python/>`_ to run
Synnefo from a cloned repo and see your changes instantly.

Synnefo installation
~~~~~~~~~~~~~~~~~~~~

There are two main ways of installing Synnefo, each of which will be described
below:

* `Existing Debian Wheezy system (snf-deploy)`_: This method requires that you
  have setup a Debian Wheezy system. On this setup, you can install Synnefo
  using ``snf-deploy``.
* `Synception (snf-ci)`_: This method builds Synnefo within Synnefo (you read
  right), which means that you need to have an account in an existing Synnefo
  installation. Then, using ``snf-ci`` in conjunction with ``kamaki``, you can
  create a new Debian Wheezy VM in that installation. The rest is handled
  automatically by ``snf-ci``, which uses ``snf-deploy`` to install Synnefo in
  that VM.

.. note::

    The first method will build Synnefo from our stable branch. If your
    development takes place in ``develop`` or in a ``feature`` branch, then you
    may need to update your installation manually, e.g. run database migrations
    or install new packages.


Existing Debian Wheezy system (snf-deploy)
------------------------------------------

**1. Install Synnefo**

In order to create a one-node Synnefo installation, you can follow the
instructions `here
<http://www.synnefo.org/docs/synnefo/latest/quick-install-guide.html>`_.

**2. Install Devflow**

Once you're done, you will need to install ``devflow``. Devflow is a tool that
helps you to manage package versions, implement the git flow development
process and build Python and Debian packages. You will need it to create your
code's version.

.. code-block:: console

   # pip install devflow


**3. Clone Synnefo repo**

First, you need to install ``git``:

.. code-block:: console

   # apt-get install git

and clone the Synnefo repo, preferably as non-privileged user:

.. code-block:: console

   $ git clone https://github.com/grnet/synnefo.git


**4. Configure the code's version**

Enter the directory where you have cloned the Synnefo repository and issue the
following command:

.. code-block:: console

   $ devflow-update-version


Synception (snf-ci)
-------------------

**1. Install Kamaki**

Kamaki is a cli tool for managing clouds. It implements the Openstack APIs and
can be used to create VMs, networks and generally allow the user to do what
he/she would normally do from the cloud's UI.

If you haven't installed ``kamaki`` yet, you can follow `these
<http://www.synnefo.org/docs/kamaki/latest/installation.html>`_ instructions.

Once you have ``kamaki`` installed, you need to connect it to your account on
an existing Synnefo installation (called *cloud* in kamaki lingo). To do so,
you can consult the `Setup
<http://www.synnefo.org/docs/kamaki/latest/setup.html#quick-setup>`_ section.
Alternative, you can visit the **API access** page of your account in that
cloud and download your personalized ``.kamakirc`` file.

**2. Clone Synnefo repo**

First you need to install ``git`` and ``fabric`` (the latter is used internally
by the ``snf-ci`` script):

.. code-block:: console

   # apt-get install git fabric

and clone the Synnefo repo, preferably as non-privileged user:

.. code-block:: console

   $ git clone https://github.com/grnet/synnefo.git


**3. Install Synnefo remotely on a VM**

Enter the directory where you have cloned the Synnefo repository and then enter
the ``ci`` folder. In this folder, you will find the ``snf-ci`` script.  A
common usage of ``snf-ci`` is the following:

.. code-block:: console

    $ ./ci/snf-ci create,build,deploy --cloud <cloud>

The above command will use your ``kamaki`` *cloud* that you have setup in
**Step 1**. In this cloud, ``snf-ci`` will create a Debian Wheezy VM, checkout
the **develop** branch from the official Synnefo repo, build the Synnefo
packages from source and install them using ``snf-deploy``. Of course, all the
previous actions can be tweaked with command-line arguments or configuration
files. To see a list of possible command-line arguments, you can use ``snf-ci
-h``. Also, you can edit the ``ci-wheezy.conf`` configuration file for more
permanent changes.

.. tip::

    You can use the **--local-repo** argument to instruct snf-ci to use the
    current branch. This means that you can install Synnefo from any branch,
    even your own.

.. tip::

    You can view details for the created VM, such as IP, username, password
    etc., by doing ``cat /tmp/ci_temp_conf``.


Development mode
~~~~~~~~~~~~~~~~

At this point you should have a working Synnefo installation. The rest of the
instructions will take place in that Synnefo installation.

**1. Use Python's development mode**

From the top directory of your Synnefo repo, you can use the following script:

.. code-block:: console

   $ ./ci/install.sh

This means that every installed ``snf-*`` package will be overridden (``python
setup.py develop -N``) with the code that exists in the currently checked-out
branch of the cloned Synnefo repo. If you wish to leave the development mode,
you can use another script:

.. code-block:: console

   $ ./ci/uninstall.sh


**2. Change Gunicorn permissions**

If you have cloned the repository as root, then Gunicorn will not be able to
read your source files, since by default its user/group permissions are
``www-data``.  However, you can change the Gunicorn permissions by editing the
``/etc/gunicorn.d/synnefo`` configuration file and replacing every ``www-data``
instance with ``root``.

.. warning::

    Gunicorn's should never run as ``root`` in production environments.

Accessing the Synnefo UI
~~~~~~~~~~~~~~~~~~~~~~~~

If you want to access the Synnefo UI through your browser, you can take a look
at the :ref:`access-synnefo` section.

Caveats regarding code changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

At this point, you would expect that every change you've made in your branch
will be instantly visible to Synnefo. Most of the times this will be the case,
but in certain circumstances you may need to restart a service or move files
around:

* If you have changed a Synnefo setting or Django view/url, you may need to
  restart Gunicorn with:

  .. code-block:: console

      # service gunicorn restart

* If your changes affected ``snf-dispatcher`` (from package
  ``snf-cyclades-app``) or ``snf-ganeti-eventd`` (from ``snf-cyclades-gtools``)
  you will need to restart these daemons, too.

  .. code-block:: console

        # service snf-dispatcher restart
        # service snf-ganeti-eventd restart

* If you have edited a static file of a Synnefo component, you will need to
  copy it to the respective folder under ``/usr/share/synnefo/static/``.


Logs
~~~~

You will find useful information for debugging in the following files:

* ``/var/log/gunicorn/synnefo.log``, for most Synnefo components.
* ``/var/log/apache2/other_vhosts_access.log``, for issues with site
  configuration.
* ``/var/log/postgresql/postgresql-9.1-main.log``, for database issues.


Testing
~~~~~~~

Synnefo has two main testing endpoints:

* The ``snf-ci`` script can create a VM from a custom branch and run all
  available tests on it.
* The ``./ci/tests.sh`` script can be used in an existing Synnefo installation
  to run all or specific tests. You can use it as following:

  .. code-block:: console

      $ ./ci/tests.sh [--dry-run] component1[.test] component2[.test] ...


