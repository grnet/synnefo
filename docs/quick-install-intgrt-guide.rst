.. _quick-install-intgrt-guide:

Integrator's Quick Installation Guide
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is the Integrator's quick installation guide.

It is intended for developers, wishing to implement new functionality
inside Synnefo. It assumes thorough familiarity with the
:ref:`Synnefo Administrator's Guide <admin-guide>`.

It describes how to install the whole synnefo stack on two (2) physical nodes,
with minimum configuration. It installs synnefo in a ``virtualenv`` using ``pip
install``, and assumes the nodes run Debian Squeeze. After successful
installation, you will have the following services running:

 * Identity Management (Astakos)
 * Object Storage Service (Pithos)
 * Compute Service (Cyclades)
 * Image Service (part of Cyclades)
 * Network Service (part of Cyclades)

and a single unified Web UI to manage them all.

The Volume Storage Service (Archipelago) and the Billing Service (Aquarium) are
not released yet.

If you just want to install the Object Storage Service (Pithos), follow the guide
and just stop after the "Testing of Pithos" section.

Building a dev environment
--------------------------

virtualenv
**********

The easiest method to deploy a development environment is using
:command:`virtualenv`. Alternatively, you can use your system's package manager
to install any dependencies of synnefo components (e.g. Macports has them all).

   .. code-block:: console
   
      $ virtualenv ~/synnefo-env
      $ source ~/synnefo-env/bin/activate
      (synnefo-env)$ 

Virtualenv creates an isolated python environment to the path you pass as the
first argument of the command. That means that all packages you install using
:command:`pip` or :command:`easy_install` will be placed in
``ENV/lib/pythonX.X/site-packages`` and their console scripts in ``ENV/bin/``.

This allows you to develop against multiple versions of packages that your
software depends on without messing with system python packages that may be
needed in specific versions for other software you have installed on your
system.

* It is also recommended to install development helpers:

  .. code-block:: console
 
     (synnefo-env)$ pip install django_extensions fabric>=1.3

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
     (synnefo-env)$ git clone https://code.grnet.gr/git/pithos pithos
   
* Install the software components you wish to work on inside the
  virtualenv, in development mode:

   .. code-block:: console
   
      (synnefo-env)$ cd snf-cyclades-app
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

  or, if you have the ``django_extensions`` and ``werkzeug`` packages installed:

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

.. _cyclades-dev-initialmigration:

Initial Migration
*****************

To initialize south migrations in your database the following commands must be
executed:

.. code-block:: console

   $ snf-manage syncdb --all      # Create / update the database with the south tables
   $ snf-manage migrate --fake    # Perform migration in the database


Note that ``--all`` and ``--fake`` arguments are only needed when you are
initializing your database. If you want to migrate a previously create databse
to the latest db scheme just run the same commands without those arguments.

If you are trying to migrate a database that already contains the changes that
applied from a specific migration script, ``south`` will probably notify you for
inconsistent db scheme, a workaround for that issue is to use ``--fake`` option
for a specific migration.

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
:ref:`cyclades-dev-initialmigration`.


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

.. warning:: This section may be out of date.

In order to get code coverage reports you need to install django-test-coverage

.. code-block:: console

   $ pip install django-test-coverage

Then configure the test runner inside Django settings:

.. code-block:: python

   TEST_RUNNER = 'django-test-coverage.runner.run_tests'


Internationalization
--------------------

This section describes how to translate static strings in Django projects:

0. From our project's base, we add directory locale

   .. code-block:: console
   
      $ mkdir locale
   
then we add on the settings.py the language code e.g.,

   .. code-block:: python
   
      LANGUAGES = (
          ('el', u'Greek'),
          ('en', u'English'),)
   
1. For each language we want to add, we run ``makemessages`` from the project's
   base:

   .. code-block:: python

      $ ./bin/django-admin.py makemessages -l el -e html,txt,py
      (./bin/django-admin.py makemessages -l el -e html,txt,py --ignore=lib/\*)

   This will add the Greek language, and we specify that :file:`*.html`,
   :file:`*.txt` and :file:`*.py` files contain translatable strings

2. We translate our strings:

   On :file:`.py` files, e.g., :file:`views.py`, first import ``gettext``:
   
   .. code-block:: python

      from django.utils.translation import gettext_lazy as _

   Then every ``string`` to be translated becomes:  ``_('string')``
   e.g.:

   .. code-block:: python

      help_text=_("letters and numbers only"))
      'title': _('Ubuntu 10.10 server 64bit'),

   On django templates (``html`` files), on the beggining of the file we add
   ``{% load i18n %}`` then rewrite every string that needs to be translated,
   as ``{% trans "string" %}``. For example: ``{% trans "Home" %}``

3. When all strings have been translated, run:

   .. code-block:: console

      $ django-admin.py makemessages -l el -e html,txt,py

   processing language ``el``. This creates (or updates) the :file:`po` file
   for the Greek language. We run this command each time we add new strings to
   be translated.  After that, we can translate our strings in the :file:`po`
   file (:file:`locale/el/LC_MESSAGES/django.po`)

4. When the :file:`po` file is ready, run
    
   .. code-block:: console

      $ ./bin/django-admin.py compilemessages

   This compiles the ``po`` files to ``mo``. Our strings will appear translated
   once we change the language (e.g., from a dropdown menu in the page)

.. seealso::
    http://docs.djangoproject.com/en/dev/topics/i18n/internationalization/


Building source packages
------------------------

.. warning:: This section may be out of date.

To create a python package from the Synnefo source code run

.. code-block:: bash

    $ cd snf-cyclades-app
    $ python setup.py sdist

this command will create a ``tar.gz`` python source package inside ``dist`` directory.


Building documentation
----------------------

Make sure you have ``sphinx`` installed.

.. code-block:: bash
    
    $ cd snf-cyclades-app/docs
    $ make html

.. note::

   The theme define in the Sphinx configuration file ``conf.py`` is ``nature``,
   not available in the version of Sphinx shipped with Debian Squeeze. Replace
   it with ``default`` to build with a Squeeze-provided Sphinx.

html files are generated in the ``snf-cyclades-app/docs/_build/html`` directory.


Continuous integration with Jenkins
-----------------------------------
.. warning:: This section may be out of date.

Preparing a GIT mirror
**********************

Jenkins cannot currently work with Git over encrypted HTTP. To solve this
problem we currently mirror the central Git repository locally on the jenkins
installation machine. To setup such a mirror do the following:

edit .netrc::

    machine code.grnet.gr
    login accountname
    password accountpasswd

Create the mirror::

    git clone --mirror https://code.grnet.gr/git/synnefo synnefo

Setup cron to pull from the mirror periodically. Ideally, Git mirror updates
should run just before Jenkins jobs check the mirror for changes::

    4,14,24,34,44,54 * * * * cd /path/to/mirror && git fetch && git remote prune origin

Jenkins setup
*************

The following instructions will setup Jenkins to run synnefo tests with the
SQLite database. To run the tests on MySQL and/or Postgres, step 5 must be
replicated. Also, the correct configuration file must be copied (line 6 of the
build script).

1. Install and start Jenkins. On Debian Squeeze:

   wget -q -O - http://pkg.jenkins-ci.org/debian/jenkins-ci.org.key | apt-key add -
   echo "deb http://pkg.jenkins-ci.org/debian binary/" >>/etc/apt/sources.list
   echo "deb http://ppa.launchpad.net/chris-lea/zeromq/ubuntu lucid main" >> /etc/apt/sources.list
   sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys C7917B12  
   sudo apt-get update
   sudo apt-get install jenkins

   Also install the following packages:

   apt-get install python-virtualenv libcurl3-gnutls libcurl3-gnutls-dev
                   uuid-dev libmysqlclient-dev libpq-dev libsqlite-dev
                   python-dev libzmq-dev

2. After Jenkins starts, go to

   http://$HOST:8080/pluginManager/

   and install the following plug-ins at

   -Jenkins Cobertura Plugin
   -Jenkins Email Extension Plugin
   -Jenkins GIT plugin
   -Jenkins SLOCCount Plug-in
   -Hudson/Jenkins Violations plugin

3. Configure the Jenkins user's Git details:
   su jenkins
   git config --global user.email "buildbot@lists.grnet.gr"
   git config --global user.name "Buildbot"

4. Make sure that all system-level dependencies specified in README.develop
   are correctly installed

5. Create a new "free-style software" job and set the following values::

    Project name: synnefo
    Source Code Management: Git
    URL of repository: Jenkins Git does not support HTTPS for checking out directly
                        from the repository. The temporary solution is to checkout
                        with a cron script in a directory and set the checkout path
                        in this field
    Branches to build: master and perhaps others
    Git->Advanced->Local subdirectory for repo (optional): synnefo
    Git->Advanced->Prune remote branches before build: check
    Repository browser: redmineweb,
                         URL: https://code.grnet.gr/projects/synnefo/repository/
    Build Triggers->Poll SCM: check
                     Schedule: # every five minutes
                   0,5,10,15,20,25,30,35,40,45,50,55 * * * * 

    Build -> Add build step-> Execute shell

    Command::

        #!/bin/bash -ex
        cd synnefo
        mkdir -p reports
        /usr/bin/sloccount --duplicates --wide --details api util ui logic auth > reports/sloccount.sc
        cp conf/ci/manage.py .
        if [ ! -e requirements.pip ]; then cp conf/ci/pip-1.2.conf requirements.pip; fi
        cat settings.py.dist conf/ci/settings.py.sqlite > settings.py
        python manage.py update_ve
        python manage.py hudson api db logic 

    Post-build Actions->Publish JUnit test result report: check
                         Test report XMLs: synnefo/reports/TEST-*.xml

    Post-build Actions->Publish Cobertura Coverage Report: check
                         Cobertura xml report pattern: synnefo/reports/coverage.xml

    Post-build Actions->Report Violations: check
                         pylint[XML filename pattern]: synnefo/reports/pylint.report

    Post-build Actions->Publish SLOCCount analysis results
                         SLOCCount reports: synnefo/reports/sloccount.sc
                         (also, remember to install sloccount at /usr/bin)

.. seealso::
    http://sites.google.com/site/kmmbvnr/home/django-hudson-tutorial
