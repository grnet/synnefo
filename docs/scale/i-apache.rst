.. _i-apache:

Synnefo
-------

:ref:`synnefo <i-synnefo>` ||
:ref:`ns <i-ns>` ||
:ref:`apt <i-apt>` ||
:ref:`mq <i-mq>` ||
:ref:`db <i-db>` ||
:ref:`gunicorn <i-gunicorn>` ||
apache ||
:ref:`webproject <i-webproject>` ||
:ref:`astakos <i-astakos>` ||
:ref:`qh <i-qh>` ||
:ref:`cms <i-cms>` ||
:ref:`pithos <i-pithos>` ||
:ref:`cyclades <i-cyclades>` ||
:ref:`kamaki <i-kamaki>` ||
:ref:`backends <i-backends>`

Apache Setup
++++++++++++

The following apply to ``astakos``, ``pithos``, ``cyclades`` and ``cms`` nodes.
Here we assume that these nodes have FQDM ``nodeX.example.com``.

First install corresponding packet:

.. code-block:: console

   # apt-get install apache2

In `/etc/apache2/sites-available/synnefo` add:

.. code-block:: console

   <VirtualHost *:80>
     ServerName nodeX.example.com

     RewriteEngine On
     RewriteRule (.*) https://%{HTTP_HOST}%{REQUEST_URI}
   </VirtualHost>

In `/etc/apache2/sites-available/synnefo-ssl` add:

.. code-block:: console

   <IfModule mod_ssl.c>
   <VirtualHost _default_:443>
     ServerName nodeX.example.com

     Alias /static "/usr/share/synnefo/static"

     AllowEncodedSlashes On

     RequestHeader set X-Forwarded-Protocol "https"

     <Proxy * >
       Order allow,deny
       Allow from all
     </Proxy>

     SetEnv                proxy-sendchunked
     SSLProxyEngine        off
     ProxyErrorOverride    off

     ProxyPass        /static !
     ProxyPass        / http://localhost:8080/ retry=0
     ProxyPassReverse / http://localhost:8080/

     SSLEngine on
     SSLCertificateFile    /etc/ssl/certs/ssl-cert-snakeoil.pem
     SSLCertificateKeyFile /etc/ssl/private/ssl-cert-snakeoil.key
   </VirtualHost>
   </IfModule>

Now enable sites and modules by running:

.. code-block:: console

   # a2enmod ssl
   # a2enmod rewrite
   # a2dissite default
   # a2ensite synnefo
   # a2ensite synnefo-ssl
   # a2enmod headers
   # a2enmod proxy_http


Test your Setup:
++++++++++++++++
