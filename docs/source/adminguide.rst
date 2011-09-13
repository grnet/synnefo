Administrator Guide
===================

Simple Setup
------------

Assuming a clean debian squeeze (stable) installation, use the following steps to run the software.

Install packages::

  apt-get install git python-django python-setuptools python-sphinx
  apt-get install python-sqlalchemy python-psycopg2
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

	DocumentRoot /var/www/pithos_web_client
	<Directory />
		Options FollowSymLinks
		AllowOverride None
	</Directory>
	<Directory /var/www/>
		Options Indexes FollowSymLinks MultiViews
		AllowOverride None
		Order allow,deny
		allow from all
	</Directory>

	Alias /docs "/pithos/docs/build/html"
	<Directory /pithos/docs/build/html/>
		Order allow,deny
		Allow from all
	</Directory>

	RewriteEngine On
	RewriteRule ^/v(.*) /api/v$1 [PT]
	RewriteRule ^/public(.*) /api/public$1 [PT]
        RewriteRule ^/login(.*) https://%{HTTP_HOST}%{REQUEST_URI}
        RewriteRule ^/admin(.*) https://%{HTTP_HOST}%{REQUEST_URI}

	<Directory /pithos/pithos/wsgi/>
		Order allow,deny
		Allow from all
	</Directory>
	WSGIScriptAlias /api /pithos/pithos/wsgi/pithos.wsgi

	# WSGIDaemonProcess pithos
	# WSGIProcessGroup pithos

	ErrorLog ${APACHE_LOG_DIR}/pithos.error.log

	# Possible values include: debug, info, notice, warn, error, crit,
	# alert, emerg.
	LogLevel warn

	CustomLog ${APACHE_LOG_DIR}/pithos.access.log combined

  </VirtualHost>

Edit ``/etc/apache2/sites-available/pithos-ssl`` (assuming files in ``/etc/ssl/private/pithos.dev.grnet.gr.key`` and ``/etc/ssl/certs/pithos.dev.grnet.gr.crt`` - change the ``ServerName`` directive)::

  <IfModule mod_ssl.c>
  <VirtualHost _default_:443>
	ServerAdmin webmaster@pithos.dev.grnet.gr
	ServerName pithos.dev.grnet.gr

	DocumentRoot /var/www/pithos_web_client
	<Directory />
		Options FollowSymLinks
		AllowOverride None
	</Directory>
	<Directory /var/www/>
		Options Indexes FollowSymLinks MultiViews
		AllowOverride None
		Order allow,deny
		allow from all
	</Directory>

	Alias /docs "/pithos/docs/build/html"
	<Directory /pithos/docs/build/html/>
		Order allow,deny
		Allow from all
	</Directory>

	RewriteEngine On
	RewriteRule ^/v(.*) /api/v$1 [PT]
	RewriteRule ^/public(.*) /api/public$1 [PT]
	RewriteRule ^/login(.*) /api/login$1 [PT]
	RewriteRule ^/admin(.*) /api/admin$1 [PT]

        <Directory /pithos/pithos/wsgi/>
                Order allow,deny
                Allow from all
        </Directory>
        WSGIScriptAlias /api /pithos/pithos/wsgi/pithos.wsgi

	ErrorLog ${APACHE_LOG_DIR}/pithos-ssl.error.log

	# Possible values include: debug, info, notice, warn, error, crit,
	# alert, emerg.
	LogLevel warn

	CustomLog ${APACHE_LOG_DIR}/pithos-ssl.access.log combined

	#   SSL Engine Switch:
	#   Enable/Disable SSL for this virtual host.
	SSLEngine on

	#   A self-signed (snakeoil) certificate can be created by installing
	#   the ssl-cert package. See
	#   /usr/share/doc/apache2.2-common/README.Debian.gz for more info.
	#   If both key and certificate are stored in the same file, only the
	#   SSLCertificateFile directive is needed.
	SSLCertificateFile    /etc/ssl/certs/pithos.dev.grnet.gr.crt
	SSLCertificateKeyFile /etc/ssl/private/pithos.dev.grnet.gr.key

	#   Server Certificate Chain:
	#   Point SSLCertificateChainFile at a file containing the
	#   concatenation of PEM encoded CA certificates which form the
	#   certificate chain for the server certificate. Alternatively
	#   the referenced file can be the same as SSLCertificateFile
	#   when the CA certificates are directly appended to the server
	#   certificate for convinience.
	#SSLCertificateChainFile /etc/apache2/ssl.crt/server-ca.crt

	#   Certificate Authority (CA):
	#   Set the CA certificate verification path where to find CA
	#   certificates for client authentication or alternatively one
	#   huge file containing all of them (file must be PEM encoded)
	#   Note: Inside SSLCACertificatePath you need hash symlinks
	#         to point to the certificate files. Use the provided
	#         Makefile to update the hash symlinks after changes.
	#SSLCACertificatePath /etc/ssl/certs/
	#SSLCACertificateFile /etc/apache2/ssl.crt/ca-bundle.crt

	#   Certificate Revocation Lists (CRL):
	#   Set the CA revocation path where to find CA CRLs for client
	#   authentication or alternatively one huge file containing all
	#   of them (file must be PEM encoded)
	#   Note: Inside SSLCARevocationPath you need hash symlinks
	#         to point to the certificate files. Use the provided
	#         Makefile to update the hash symlinks after changes.
	#SSLCARevocationPath /etc/apache2/ssl.crl/
	#SSLCARevocationFile /etc/apache2/ssl.crl/ca-bundle.crl

	#   Client Authentication (Type):
	#   Client certificate verification type and depth.  Types are
	#   none, optional, require and optional_no_ca.  Depth is a
	#   number which specifies how deeply to verify the certificate
	#   issuer chain before deciding the certificate is not valid.
	#SSLVerifyClient require
	#SSLVerifyDepth  10

	#   Access Control:
	#   With SSLRequire you can do per-directory access control based
	#   on arbitrary complex boolean expressions containing server
	#   variable checks and other lookup directives.  The syntax is a
	#   mixture between C and Perl.  See the mod_ssl documentation
	#   for more details.
	#<Location />
	#SSLRequire (    %{SSL_CIPHER} !~ m/^(EXP|NULL)/ \
	#            and %{SSL_CLIENT_S_DN_O} eq "Snake Oil, Ltd." \
	#            and %{SSL_CLIENT_S_DN_OU} in {"Staff", "CA", "Dev"} \
	#            and %{TIME_WDAY} >= 1 and %{TIME_WDAY} <= 5 \
	#            and %{TIME_HOUR} >= 8 and %{TIME_HOUR} <= 20       ) \
	#           or %{REMOTE_ADDR} =~ m/^192\.76\.162\.[0-9]+$/
	#</Location>

	#   SSL Engine Options:
	#   Set various options for the SSL engine.
	#   o FakeBasicAuth:
	#     Translate the client X.509 into a Basic Authorisation.  This means that
	#     the standard Auth/DBMAuth methods can be used for access control.  The
	#     user name is the `one line' version of the client's X.509 certificate.
	#     Note that no password is obtained from the user. Every entry in the user
	#     file needs this password: `xxj31ZMTZzkVA'.
	#   o ExportCertData:
	#     This exports two additional environment variables: SSL_CLIENT_CERT and
	#     SSL_SERVER_CERT. These contain the PEM-encoded certificates of the
	#     server (always existing) and the client (only existing when client
	#     authentication is used). This can be used to import the certificates
	#     into CGI scripts.
	#   o StdEnvVars:
	#     This exports the standard SSL/TLS related `SSL_*' environment variables.
	#     Per default this exportation is switched off for performance reasons,
	#     because the extraction step is an expensive operation and is usually
	#     useless for serving static content. So one usually enables the
	#     exportation for CGI and SSI requests only.
	#   o StrictRequire:
	#     This denies access when "SSLRequireSSL" or "SSLRequire" applied even
	#     under a "Satisfy any" situation, i.e. when it applies access is denied
	#     and no other module can change it.
	#   o OptRenegotiate:
	#     This enables optimized SSL connection renegotiation handling when SSL
	#     directives are used in per-directory context.
	#SSLOptions +FakeBasicAuth +ExportCertData +StrictRequire
	<FilesMatch "\.(cgi|shtml|phtml|php)$">
		SSLOptions +StdEnvVars
	</FilesMatch>
	<Directory /usr/lib/cgi-bin>
		SSLOptions +StdEnvVars
	</Directory>

	#   SSL Protocol Adjustments:
	#   The safe and default but still SSL/TLS standard compliant shutdown
	#   approach is that mod_ssl sends the close notify alert but doesn't wait for
	#   the close notify alert from client. When you need a different shutdown
	#   approach you can use one of the following variables:
	#   o ssl-unclean-shutdown:
	#     This forces an unclean shutdown when the connection is closed, i.e. no
	#     SSL close notify alert is send or allowed to received.  This violates
	#     the SSL/TLS standard but is needed for some brain-dead browsers. Use
	#     this when you receive I/O errors because of the standard approach where
	#     mod_ssl sends the close notify alert.
	#   o ssl-accurate-shutdown:
	#     This forces an accurate shutdown when the connection is closed, i.e. a
	#     SSL close notify alert is send and mod_ssl waits for the close notify
	#     alert of the client. This is 100% SSL/TLS standard compliant, but in
	#     practice often causes hanging connections with brain-dead browsers. Use
	#     this only for browsers where you know that their SSL implementation
	#     works correctly.
	#   Notice: Most problems of broken clients are also related to the HTTP
	#   keep-alive facility, so you usually additionally want to disable
	#   keep-alive for those clients, too. Use variable "nokeepalive" for this.
	#   Similarly, one has to force some clients to use HTTP/1.0 to workaround
	#   their broken HTTP/1.1 implementation. Use variables "downgrade-1.0" and
	#   "force-response-1.0" for this.
	BrowserMatch "MSIE [2-6]" \
		nokeepalive ssl-unclean-shutdown \
		downgrade-1.0 force-response-1.0
	# MSIE 7 and newer should be able to use keepalive
	BrowserMatch "MSIE [17-9]" ssl-unclean-shutdown

  </VirtualHost>
  </IfModule>

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

MySQL Setup
-----------

If using MySQL instead of SQLite for the database engine, consider the following.

Server side::

  apt-get install mysql-server

Edit ``/etc/mysql/my.cnf`` to allow network connections and restart the server.

Create database and user::

  CREATE DATABASE pithos;
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

