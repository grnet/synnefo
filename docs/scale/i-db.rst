.. _i-db:

Synnefo
-------

:ref:`synnefo <i-synnefo>` ||
:ref:`ns <i-ns>` ||
:ref:`apt <i-apt>` ||
:ref:`mq <i-mq>` ||
db ||
:ref:`gunicorn <i-gunicorn>` ||
:ref:`apache <i-apache>` ||
:ref:`webproject <i-webproject>` ||
:ref:`astakos <i-astakos>` ||
:ref:`cms <i-cms>` ||
:ref:`pithos <i-pithos>` ||
:ref:`cyclades <i-cyclades>` ||
:ref:`kamaki <i-kamaki>` ||
:ref:`backends <i-backends>`

Database Setup
++++++++++++++

The following apply to ``db`` node. For the rest of the sections we will
refer to its IP as ``db.example.com`` .

First install progresql:

.. code-block:: console

   # apt-get install postgresql

We create a database called ``snf_apps``, that will host all django
apps related tables. We also create the user ``synnefo`` and grant him all
privileges on the database. We do this by running:

.. code-block:: console

   # su - postgres
   postgres:~$ psql
   postgres=# CREATE DATABASE snf_apps WITH ENCODING 'UTF8' LC_COLLATE='C' LC_CTYPE='C' TEMPLATE=template0;
   postgres=# CREATE USER synnefo WITH PASSWORD 'example_passw0rd';
   postgres=# GRANT ALL PRIVILEGES ON DATABASE snf_apps TO synnefo;

We also create the database ``snf_pithos`` needed by the Pithos backend and
grant the ``synnefo`` user all privileges on the database.

.. code-block:: console

   postgres=# CREATE DATABASE snf_pithos WITH ENCODING 'UTF8' LC_COLLATE='C' LC_CTYPE='C' TEMPLATE=template0;
   postgres=# GRANT ALL PRIVILEGES ON DATABASE snf_pithos TO synnefo;

Configure the database to listen to all network interfaces. You can do this by
editting the file `/etc/postgresql/8.4/main/postgresql.conf` with:

| ``listen_addresses = '*'``

Furthermore, edit `/etc/postgresql/8.4/main/pg_hba.conf` to allow the nodes
to connect to the database. Add the following line:

| ``host		all	all	4.3.2.0/24	md5``

.. code-block:: console

   # /etc/init.d/postgresql restart


Test your Setup:
++++++++++++++++
