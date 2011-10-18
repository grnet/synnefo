Administrator Guide
===================

Simple Setup
------------

Assuming a clean debian squeeze (stable) installation, use the following steps to run the software.

Install packages::

  apt-get install git python-django python-setuptools python-sphinx
  apt-get install python-sqlalchemy python-mysqldb python-psycopg2
  apt-get install apache2 libapache2-mod-wsgi

Get the source::

  cd /
  git clone https://code.grnet.gr/git/pithos

Setup the files (choose where to store data in ``settings.py`` and change ``SECRET_KEY``)::

  cd /pithos/pithos
  cp settings.py.dist settings.py
  python manage.py syncdb
  cd /pithos
  python setup.py build_sphinx

Edit ``/etc/apache2/sites-available/pithos`` (change the ``ServerName`` directive)::

  <VirtualHost *:80>
    ServerAdmin webmaster@pithos.dev.grnet.gr
    ServerName pithos.dev.grnet.gr

    DocumentRoot /pithos/htdocs
    Alias /ui "/var/www/pithos_web_client"
    Alias /docs "/pithos/docs/build/html"

    <Directory />
        Options Indexes FollowSymLinks
        AllowOverride None
        Order allow,deny
        Allow from all
    </Directory>

    RewriteEngine On
    RewriteRule ^/v(.*) /api/v$1 [PT]
    RewriteRule ^/public(.*) /api/public$1 [PT]
    RewriteRule ^/login(.*) https://%{HTTP_HOST}%{REQUEST_URI}
    RewriteRule ^/admin(.*) https://%{HTTP_HOST}%{REQUEST_URI}

    WSGIScriptAlias /api /pithos/pithos/wsgi/pithos.wsgi
    # WSGIDaemonProcess pithos
    # WSGIProcessGroup pithos

    LogLevel warn
    ErrorLog ${APACHE_LOG_DIR}/pithos.error.log
    CustomLog ${APACHE_LOG_DIR}/pithos.access.log combined
  </VirtualHost>

Edit ``/etc/apache2/sites-available/pithos-ssl`` (assuming files in ``/etc/ssl/private/pithos.dev.grnet.gr.key`` and ``/etc/ssl/certs/pithos.dev.grnet.gr.crt`` - change the ``ServerName`` directive)::

  <IfModule mod_ssl.c>
  <VirtualHost _default_:443>
    ServerAdmin webmaster@pithos.dev.grnet.gr
    ServerName pithos.dev.grnet.gr

    DocumentRoot /pithos/htdocs
    Alias /ui "/var/www/pithos_web_client"
    Alias /docs "/pithos/docs/build/html"

    <Directory />
        Options Indexes FollowSymLinks
        AllowOverride None
        Order allow,deny
        Allow from all
    </Directory>

    RewriteEngine On
    RewriteRule ^/v(.*) /api/v$1 [PT]
    RewriteRule ^/public(.*) /api/public$1 [PT]
    RewriteRule ^/login(.*) /api/login$1 [PT]
    RewriteRule ^/admin(.*) /api/admin$1 [PT]

    WSGIScriptAlias /api /pithos/pithos/wsgi/pithos.wsgi
    # WSGIDaemonProcess pithos
    # WSGIProcessGroup pithos

    ShibConfig /etc/shibboleth/shibboleth2.xml
    Alias      /shibboleth-sp /usr/share/shibboleth 

    <Location /api/login>
        AuthType shibboleth
        ShibRequireSession On
        ShibUseHeaders On
        require valid-user
    </Location>

    LogLevel warn
    ErrorLog ${APACHE_LOG_DIR}/pithos.error.log
    CustomLog ${APACHE_LOG_DIR}/pithos.access.log combined

    SSLEngine on
    SSLCertificateFile    /etc/ssl/certs/pithos.dev.grnet.gr.crt
    SSLCertificateKeyFile /etc/ssl/private/pithos.dev.grnet.gr.key
  </VirtualHost>
  </IfModule>

Add in ``/etc/apache2/mods-available/wsgi.conf``::

  WSGIChunkedRequest On

Configure and run apache::

  a2enmod ssl
  a2enmod rewrite
  a2dissite default
  a2ensite pithos
  a2ensite pithos-ssl
  mkdir /var/www/pithos
  mkdir /var/www/pithos_web_client
  /etc/init.d/apache2 restart

Useful alias to add in ``~/.bashrc``::

  alias pithos-sync='cd /pithos && git pull && python setup.py build_sphinx && /etc/init.d/apache2 restart'

Gunicorn Setup
--------------

Add in ``/etc/apt/sources.list``::

  deb http://backports.debian.org/debian-backports squeeze-backports main

Then::

  apt-get update
  apt-get -t squeeze-backports install gunicorn
  apt-get -t squeeze-backports install python-gevent

Create ``/etc/gunicorn.d/pithos``::

  CONFIG = {
   'mode': 'django',
   'working_dir': '/pithos/pithos',
   'user': 'www-data',
   'group': 'www-data',
   'args': (
        '--bind=[::]:8080',
        '--worker-class=egg:gunicorn#gevent',
        '--workers=4',
        '--log-level=debug',
        '/pithos/pithos/settings.py',
   ),
  }

Replace the ``WSGI*`` directives in ``/etc/apache2/sites-available/pithos`` and ``/etc/apache2/sites-available/pithos-ssl`` with::

  <Proxy *>
    Order allow,deny
    Allow from all
  </Proxy>

  SetEnv                proxy-sendchunked
  SSLProxyEngine        off
  ProxyErrorOverride    off

  ProxyPass        /api http://localhost:8080 retry=0
  ProxyPassReverse /api http://localhost:8080

Configure and run::

  /etc/init.d/gunicorn restart
  a2enmod proxy
  a2enmod proxy_http
  /etc/init.d/apache2 restart

Shibboleth Setup
----------------

Install package::

  apt-get install libapache2-mod-shib2

Setup the files in ``/etc/shibboleth``.

Add in ``/etc/apache2/sites-available/pithos-ssl``::

  ShibConfig /etc/shibboleth/shibboleth2.xml
  Alias      /shibboleth-sp /usr/share/shibboleth 

  <Location /api/login>
    AuthType shibboleth
    ShibRequireSession On
    ShibUseHeaders On
    require valid-user
  </Location>

Configure and run apache::

  a2enmod shib2
  /etc/init.d/apache2 restart
  /etc/init.d/shibd restart

The following tokens should be available at the destination, after passing through the apache module::

  eppn # eduPersonPrincipalName
  Shib-InetOrgPerson-givenName
  Shib-Person-surname
  Shib-Person-commonName
  Shib-InetOrgPerson-displayName
  Shib-EP-Affiliation
  Shib-Session-ID

MySQL Setup
-----------

If using MySQL instead of SQLite for the database engine, consider the following.

Server side::

  apt-get install mysql-server

Add in ``/etc/mysql/conf.d/pithos.cnf``::

  [mysqld]
  sql-mode="NO_AUTO_VALUE_ON_ZERO"

Edit ``/etc/mysql/my.cnf`` to allow network connections and restart the server.

Create database and user::

  CREATE DATABASE pithos CHARACTER SET utf8 COLLATE utf8_bin;
  GRANT ALL ON pithos.* TO pithos@localhost IDENTIFIED BY 'password';
  GRANT ALL ON pithos.* TO pithos@'%' IDENTIFIED BY 'password';

Client side::

  apt-get install mysql-client

It helps to create a ``~/.my.cnf`` file, for automatically connecting to the server::

  [client]
  user = pithos
  password = 'password'
  host = pithos-storage.dev.grnet.gr

  [mysql]
  database = pithos

PostgreSQL Setup
----------------

If using PostgreSQL instead of SQLite for the database engine, consider the following.

Server side::

  apt-get install postgresql

Edit ``/etc/postgresql/8.4/main/postgresql.conf`` and ``/etc/postgresql/8.4/main/pg_hba.conf`` to allow network connections and restart the server.

Create database and user::

  CREATE DATABASE pithos WITH ENCODING 'UTF8' LC_COLLATE='C' LC_CTYPE='C' TEMPLATE=template0;
  CREATE USER pithos WITH PASSWORD 'password';
  GRANT ALL PRIVILEGES ON DATABASE pithos TO pithos;

Client side::

  apt-get install postgresql-client

It helps to create a ``~/.pgpass`` file, for automatically passing the password to the server::

  pithos-storage.dev.grnet.gr:5432:pithos:pithos:password

Connect with::

  psql -h pithos-storage.dev.grnet.gr -U pithos

