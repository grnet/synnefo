Developers guide
================

Information on how to setup a development environment.

This file documents the installation of a development environment for Synnefo.
It should be read alongside :ref:`installation guide <installation>`.

It contains development-specific ammendments to the basic installation steps
outlined in `installation guide <installation>`, and development-specific notes.


Prerequisites
-------------

For a basic development environment you need to follow steps
of `installation guide <installation>`, which should be read 
in its entirety *before* this document.


Setting up development environment
----------------------------------

Although not necessary it is suggested that you use a virtualenv as a base for
your development environment::

    $ virtualenv synnefo-env
    $ cd synnefo-dev
    $ source bin/activate

* Clone Synnefo repository::

  (synnefo-env)$ git clone https://code.grnet.gr/git/synnefo synnefo

* Install synnefo depedencies::

  (synnefo-env)$ pip install -r synnefo/requirements.pip

* Install development helpers::

  (synnefo-env)$ pip install django_extensions

* Install synnefo package::

  (synnefo-env)$ cd synnefo/snf-app
  (synnefo-env)$ python setup.py develop -N

* Create a custom development settings module and set environment variable to
  use this module as the entry point of synnefo settings::

  (synnefo-env)$ touch settings_dev.py
  (synnefo-env)$ export DJANGO_SETTINGS_MODULE=settings_dev
  (synnefo-env)$ export PYTHONPATH=`pwd`:$PYTHONPATH
  (synnefo-env)$ vi settings_dev.py
    
  paste the following sample development settings:

  .. code-block:: python
    
        import os

        from synnefo.settings.common import *
        
        # uncomment this if have django-extensions installed (pip install django_extensions)
        #INSTALLED_APPS = list(INSTALLED_APPS) + ['django_extensions']

        DEV_PATH = os.path.abspath(os.path.dirname(__file__))
        DATABASES['default']['NAME'] = os.path.join(DEV_PATH, "synnefo.sqlite")


        # development rabitmq configuration
        RABBIT_HOST = ""
        RABBIT_USERNAME = ""
        RABBIT_PASSWORD = ""
        RABBIT_VHOST = "/"

        # development ganeti settings
        GANETI_MASTER_IP = ""
        GANETI_CLUSTER_INFO = (GANETI_MASTER_IP, 5080, "<username>", "<password>")
        GANETI_CREATEINSTANCE_KWARGS['disk_template'] = 'plain'

        # This prefix gets used when determining the instance names
        # of Synnefo VMs at the Ganeti backend.
        # The dash must always appear in the name!
        BACKEND_PREFIX_ID = "<my commit name>-"

        IGNORE_FLAVOR_DISK_SIZES = True

        # do not actually send emails
        # save them as files in /tmp/synnefo-mails
        EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
        EMAIL_FILE_PATH = '/tmp/synnefo-mails'

        # for UI developers
        UI_HANDLE_WINDOW_EXCEPTIONS = False

        # allow login using /?test url
        BYPASS_AUTHENTICATION = True 

* Initialize database::

  (synnefo-env)$ synnefo-manage syndb
  (synnefo-env)$ synnefo-manage migrate
  (synnefo-env)$ synnefo-manage loaddata users flavors images


Development tips
****************

* Running a development web server::

  (synnefo-env)$ synnefo-manage runserver

  or, if you have django_extensions and werkzeug packages installed::

  (synnefo-env)$ synnefo-manage runserver_plus


* Opening a python console with synnefo environment initialized::

  (synnefo-env)$ synnefo-manage shell

  or, if you have django_extensions package installed::

  (synnefo-env)$ synnefo-manage shell_plus


South Database Migrations
-------------------------

Initial Migration
*****************

To initialise south migrations in your database the following commands must be
executed::

    $ synnefo-manage syncdb       # Create / update the database with the south tables
    $ synnefo-manage migrate db   # Perform migration in the database

Note that syncdb will create the latest models that exist in the db app, so some
migrations may fail.  If you are sure a migration has already taken place you
must use the "--fake" option, to apply it.

For example::

    $ synnefo-manage migrate db 0001 --fake

To be sure that all migrations are applied type::

    $ synnefo-manage migrate db --list

All starred migrations are applied.

Remember, the migration is performed mainly for the data, not for the database
schema. If you do not want to migrate the data, a syncdb and fake migrations for
all the migration versions will suffice.

Schema migrations
*****************

Do not use the syncdb management command. It can only be used the first time
and/or if you drop the database and must recreate it from scratch. See
"Initial Migration" section.

Every time you make changes to the database and data migration is not required
(WARNING: always perform this with extreme care)::

    $ synnefo-manage schemamigration db --auto

The above will create the migration script. Now this must be applied to the live
database::

    $ synnefo-manage migrate db

Consider this example (adding a field to the SynnefoUser model)::

    $ ./bin/python manage.py schemamigration db --auto
     + Added field new_south_test_field on db.SynnefoUser

     Created 0002_auto__add_field_synnefouser_new_south_test_field.py.

You can now apply this migration with::

    $ ./manage.py migrate db
     Running migrations for db:
     - Migrating forwards to 0002_auto__add_field_synnefouser_new_south_test_field.
     > db:0002_auto__add_field_synnefouser_new_south_test_field
     - Loading initial data for db.

    Installing json fixture 'initial_data' from '/home/bkarak/devel/synnefo/../synnefo/db/fixtures'.
    Installed 1 object(s) from 1 fixture(s)

South needs some extra definitions to the model to preserve and migrate the
existing data, for example, if we add a field in a model, we should declare its
default value. If not, South will propably fail, after indicating the error::

    $ ./bin/python manage.py schemamigration db --auto
     ? The field 'SynnefoUser.new_south_field_2' does not have a default specified, yet is NOT NULL.
     ? Since you are adding or removing this field, you MUST specify a default
     ? value to use for existing rows. Would you like to:
     ?  1. Quit now, and add a default to the field in models.py
     ?  2. Specify a one-off value to use for existing columns now
     ? Please select a choice: 1

Data migrations
***************

If we need to do data migration as well, for example rename a field, we use the
'datamigration' management command.

In contrast with schemamigration, to perform complex data migration, we must
write the script manually. The process is the following:

1. Introduce the changes in the code and fixtures (initial data).
2. Execute::

    $ ./bin/python manage.py datamigration <migration_name_here>

    For example::

        $ ./bin/python manage.py datamigration db rename_credit_wallet
        Created 0003_rename_credit_wallet.py.

3. We edit the generated script. It contains two methods: forwards and
   backwards.

   For database operations (column additions, alter tables etc) we use the
   South database API (http://south.aeracode.org/docs/databaseapi.html).

   To access the data, we use the database reference (orm) provided as
   parameter in forwards, backwards method declarations in the migration
   script. For example::

        .. code-block:: python

            class Migration(DataMigration):

            def forwards(self, orm):
                orm.SynnefoUser.objects.all()

    4. To migrate the database to the latest version, we execute::

        $ synnefo-manage migrate db

    To see which migrations are applied::

          $ synnefo-manage migrate db --list

          db
            (*) 0001_initial
            (*) 0002_auto__add_field_synnefouser_new_south_test_field
            (*) 0003_rename_credit_wallet

.. seealso::
    More information and more thorough examples can be found in the South web site.
    http://south.aeracode.org/


Test coverage
-------------

In order to get code coverage reports you need to install django-test-coverage::

   $ ./bin/pip install django-test-coverage

Then edit your settings.py and configure the test runner::

   TEST_RUNNER = 'django-test-coverage.runner.run_tests'


.. include:: i18n.rst


Building Synnefo package
------------------------

To create a python package from the Synnefo source code run::
    
    $ cd snf-app
    $ python setup.py sdist

this command will create a ``tar.gz`` python source package inside ``dist`` directory.


Building Synnefo documentation
------------------------------

Make sure you have ``sphinx`` installed.

.. code-block:: bash
    
    $ cd snf-app/docs
    $ make html

html files are generated in ``snf-app/docs/_build/html`` directory

.. include:: ci.rst
