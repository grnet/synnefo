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
your development environment.

Development-specific guidelines on each step:


0. Allocation of physical nodes:
   Node types DB, APISERVER, LOGIC may all be run on the same physical machine,
   usually, your development workstation.

   Nodes of type GANETI-MASTER, GANETI-NODES and QUEUE are already provided
   by the development Ganeti backend. Access credentials are provided in
   settings.py.dist.


1. You do not need to install your own Ganeti installation.
   Use the RAPI endpoint as contained in common settings.


2. You do not need to setup your own RabbitMQ nodes, use the AMQP endpoints
   contained in settings.py.dist. 

3. For development purposes, Django's own development
   server, `./manage.py runserver` will suffice.


4. Use a virtual environment to install the Django project, or packages provided
   by your distribution.


5. Install a DB of your own, or use the PostgreSQL instance available on the
   development backend.


6. As is.


7. The following fixtures can be loaded optionally depending on
   testing/development requirements, and are not needed in a production setup:

	$ ./bin/python manage.py loaddata db/fixtures/vms.json
	$ ./bin/python manage.py loaddata db/fixtures/disks.json


8. MAKE SURE you setup a distinct BACKEND_PREFIX_ID, e.g., use your commit
   username. 


9. The Ganeti monitoring daemon from the latest Synnefo release is already
   running on the development Ganeti master. You may also run your own, on your
   own Ganeti backend if you so wish.


10. As is.

11. The Synnefo Ganeti hook is already running on the development backend,
    sending notifications over AMQP.


12. The VNC authentication proxy is already running on the Ganeti development
    backend. You *cannot* run your own, unless you install your own Ganeti
    backend, because it needs direct access to the hypervisor's VNC port on
    GANETI-NODEs.

    Note: You still need to install the vncauthproxy package to satisfy
    the dependency of the API on the vncauthproxy client. See Synnefo #807
    for more details.


13. The development Ganeti backend already has a number of OS Images available.


14. The development Ganeti backend already has a number of pre-provisioned
    bridges available, per each BACKEND_PREFIX_ID.

    To setup simple NAT-based networking on a Ganeti backend on your own,
    please see the provided patches under contrib/patches/.
    You will need minor patches to the sample KVM ifup hook, kvm-vif-bridge,
    and a small patch to NFDHCPD to enable it to work with bridged tap+
    interfaces. To support bridged tap interfaces you also need to patch the
    python-nfqueue package, patches against python-nfqueue-0.3 [part of Debian
    Sid] are also provided under contrib/patches/.


15. As is.


16. As is.


17. [OPTIONAL] Create settings.d/99-local.conf and insert local overrides for
    settings.d/\*.  This will allow pulling new files without needing to reapply
    local any local modifications.


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
