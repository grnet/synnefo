.. _asterias-developer-guide:

===============
Developer Guide
===============

This is the asterias developer guide.

It is intended for developers, wishing to implement new functionality
inside :ref:`asterias <asterias>`.

It assumes thorough familiarity with the :ref:`asterias-admin-guide`.

It contains development-specific ammendments to the basic installation steps
outlined in `installation guide <installation>`, and development-specific
notes.

Building a dev environment
--------------------------

virtualenv
**********

The easiest method to deploy a development environment is using
:command:`virtualenv`. Alternatively, you can use your system's package manager
to install any dependencies of synnefo components (e.g. Macports has them all).

   .. code-block:: console
   
      $ virtualenv ~/synnefo-env
      $ . ~/synnefo-env/bin/activate
      (synnefo-env)$ 
   
Any :command:`pip` commands executed from now on, affect the ``synnefo-env``
virtualenv.

* It is also recommended to install development helpers:

  .. code-block:: console
 
     (synnefo-env)$ pip install django_extensions

* Create a custom settings directory for :ref:`snf-common <snf-common>` and set
  the ``SYNNEFO_SETTINGS_DIR`` environment variable to use development-specific
  file:`*.conf` files inside this directory.

  (synnefo-env)$ mkdir ~/synnefo-settings-dir
  (synnefo-env)$ export SYNNEFO_SETTINGS_DIR=~/synnefo-settings-dir
    
  Insert your custom settings in a file such as :file:`$SYNNEFO_SETTINGS_DIR/99-local.conf`:

  .. code-block:: python
    
        # uncomment this if have django-extensions installed (pip install django_extensions)
        #INSTALLED_APPS = list(INSTALLED_APPS) + ['django_extensions']

        DEV_PATH = os.path.abspath(os.path.dirname(__file__))
        DATABASES['default']['NAME'] = os.path.join(DEV_PATH, "synnefo.sqlite")

        # development rabitmq configuration
        RABBIT_HOST = "<RabbitMQ_host>"
        RABBIT_USERNAME = "<RabbitMQ_username>"
        RABBIT_PASSWORD = "<RabbitMQ_password>"
        RABBIT_VHOST = "/"

        # development ganeti settings
        GANETI_MASTER_IP = "<Ganeti_master_IP>"
        GANETI_CLUSTER_INFO = (GANETI_MASTER_IP, 5080, "<username>", "<password>")
        GANETI_CREATEINSTANCE_KWARGS['disk_template'] = 'plain'

        # This prefix gets used when determining the instance names
        # of Synnefo VMs at the Ganeti backend.
        # The dash must always appear in the name!
        BACKEND_PREFIX_ID = "<your_commit_name>-"

        IGNORE_FLAVOR_DISK_SIZES = True

        # do not actually send emails
        # save them as files in /tmp/synnefo-mails
        EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
        EMAIL_FILE_PATH = '/tmp/synnefo-mails'

        # for UI developers
        UI_HANDLE_WINDOW_EXCEPTIONS = False

        # allow login using /?test url
        BYPASS_AUTHENTICATION = True 

synnefo source
**************

* Clone the repository of the synnefo software components you wish
  to work on, e.g.:

   .. code-block:: console
   
     (synnefo-env)$ git clone https://code.grnet.gr/git/synnefo synnefo
   
* Install the software components you wish to work on inside the
  virtualenv, in development mode:

   .. code-block:: console
   
      (synnefo-env)$ cd snf-asterias-app
      (synnefo-env)$ python setup.py develop -N
   
* Initialize database:

   .. code-block:: console
     
      (synnefo-env)$ snf-manage syndb
      (synnefo-env)$ snf-manage migrate
      (synnefo-env)$ snf-manage loaddata users flavors images
  
Development tips
****************

* Running a development web server:

  .. code-block:: console

     (synnefo-env)$ snf-manage runserver

  or, if you have the django_extensions and werkzeug packages installed:

  .. code-block:: console

     (synnefo-env)$ snf-manage runserver_plus

* Opening a python console with the synnefo environment initialized:

  .. code-block:: console

     (synnefo-env)$ snf-manage shell

  or, with the django_extensions package installed:

  .. code-block:: console
     
     (synnefo-env)$ snf-manage shell_plus


South Database Migrations
-------------------------

.. _asterias-dev-initialmigration:

Initial Migration
*****************

To initialize south migrations in your database the following commands must be
executed:

.. code-block:: console

   $ snf-manage syncdb       # Create / update the database with the south tables
   $ snf-manage migrate      # Perform migration in the database

Note that syncdb will create the latest models that exist in the db app, so some
migrations may fail.  If you are sure a migration has already taken place you
must use the ``--fake`` option, to apply it.

For example:


.. code-block:: console

   $ snf-manage migrate db 0001 --fake

To be sure that all migrations are applied use:

.. code-block:: console

   $ snf-manage migrate db --list

All starred migrations are applied.

Schema migrations
*****************

Do not use the syncdb management command. It can only be used the first time
and/or if you drop the database and must recreate it from scratch. See
:ref:`asterias-dev-initialmigration`.


Every time you make changes to the database and data migration is not required
(WARNING: always perform this with extreme care):

.. code-block:: console
   
   $ snf-manage schemamigration db --auto

The above will create the migration script. Now this must be applied to the live
database:

.. code-block:: console

   $ snf-manage migrate db

Consider this example (adding a field to the ``SynnefoUser`` model):

.. code-block:: console

   $ ./bin/python manage.py schemamigration db --auto
   + Added field new_south_test_field on db.SynnefoUser

   Created 0002_auto__add_field_synnefouser_new_south_test_field.py.

You can now apply this migration with:

.. code-block:: console

   $ ./manage.py migrate db
   Running migrations for db:
   - Migrating forwards to 0002_auto__add_field_synnefouser_new_south_test_field.
   > db:0002_auto__add_field_synnefouser_new_south_test_field
   - Loading initial data for db.

   Installing json fixture 'initial_data' from '/home/bkarak/devel/synnefo/../synnefo/db/fixtures'.
   Installed 1 object(s) from 1 fixture(s)

South needs some extra definitions to the model to preserve and migrate the
existing data, for example, if we add a field in a model, we should declare its
default value. If not, South will propably fail, after indicating the error:

.. code-block:: console

   $ ./bin/python manage.py schemamigration db --auto
   ? The field 'SynnefoUser.new_south_field_2' does not have a default specified, yet is NOT NULL.
   ? Since you are adding or removing this field, you MUST specify a default
   ? value to use for existing rows. Would you like to:
   ?  1. Quit now, and add a default to the field in models.py
   ?  2. Specify a one-off value to use for existing columns now
   ? Please select a choice: 1

Data migrations
***************

To do data migration as well, for example rename a field, use the
``datamigration`` management command.

In contrast with ``schemamigration``, to perform complex data migration, we
must write the script manually. The process is the following:

1. Introduce the changes in the code and fixtures (initial data).
2. Execute:

   .. code-block:: console

      $ snf-manage datamigration <migration_name_here>

   For example:

   .. code-block:: console

      $ ./bin/python manage.py datamigration db rename_credit_wallet
      Created 0003_rename_credit_wallet.py.

3. Edit the generated script. It contains two methods, ``forwards`` and
   ``backwards``.

   For database operations (column additions, alter tables etc), use the
   South database API (http://south.aeracode.org/docs/databaseapi.html).

   To access the data, use the database reference (``orm``) provided as
   parameter in ``forwards``, ``backwards`` method declarations in the
   migration script. For example:

   .. code-block:: python

      class Migration(DataMigration):

      def forwards(self, orm):
          orm.SynnefoUser.objects.all()

4. To migrate the database to the latest version, run:

   .. code-block:: console     
     
      $ snf-manage migrate db

   To see which migrations are applied:

   .. code-block:: console

      $ snf-manage migrate db --list

      db
        (*) 0001_initial
        (*) 0002_auto__add_field_synnefouser_new_south_test_field
        (*) 0003_rename_credit_wallet

.. seealso::
    More information and more thorough examples can be found in the South web site,
    http://south.aeracode.org/

Test coverage
-------------

In order to get code coverage reports you need to install django-test-coverage

.. code-block:: console

   $ pip install django-test-coverage

Then configure the test runner inside Django settings:

.. code-block:: python

   TEST_RUNNER = 'django-test-coverage.runner.run_tests'

.. include:: i18n.rst


Building Synnefo package
------------------------

To create a python package from the Synnefo source code run

.. code-block:: bash

    $ cd snf-app
    $ python setup.py sdist

this command will create a ``tar.gz`` python source package inside ``dist`` directory.


Building Synnefo documentation
------------------------------

Make sure you have ``sphinx`` installed.

.. code-block:: bash
    
    $ cd snf-app/docs
    $ make html

.. note::

   The theme define in the Sphinx configuration file ``conf.py`` is ``nature``,
   not available in the version of Sphinx shipped with Debian Squeeze. Replace
   it with ``default`` to build with a Squeeze-provided Sphinx.

html files are generated in the ``snf-app/docs/_build/html`` directory.

.. include:: ci.rst
