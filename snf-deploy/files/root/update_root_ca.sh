DIR=/root/ca

# For apache
cp -v $DIR/cacert.pem /etc/ssl/certs/synnefo_ca.pem
cp -v $DIR/key.pem /etc/ssl/private/synnefo.key
cp -v $DIR/cert.pem  /etc/ssl/certs/synnefo.pem
/etc/init.d/apache2 restart

# For kamaki
cp -v $DIR/cacert.pem /usr/local/share/ca-certificates/Synnefo_Root_CA.crt
rm -v /etc/ssl/certs/Synnefo_Root_CA.pem
rm -v /etc/ssl/certs/ca-certificates.crt
update-ca-certificates

# For vncauthproxy
cp -v $DIR/cert.pem /var/lib/vncauthproxy/cert.pem
cp -v $DIR/key.pem /var/lib/vncauthproxy/key.pem
/etc/init.d/vncauthproxy restart
/etc/init.d/gunicorn restart
