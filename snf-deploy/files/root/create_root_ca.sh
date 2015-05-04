#!/bin/bash

# THIS SCRIPT CREATES A CA AND SIGNES A CERTIFICATE TO BE USED
# FOR THE SYNNEFO INSTALLATION. IT FOLLOWS INSTRUCTIONS FROM:
# https://wiki.mozilla.org/SecurityEngineering/x509Certs#Running_your_Own_CA

DIR=/root/ca

ROOT_CA_KEY=$DIR/cakey.pem
ROOT_CA_CSR=$DIR/cacert.csr
ROOT_CA_CERT=$DIR/cacert.pem
KEY=$DIR/key.pem
CSR=$DIR/cert.csr
CERT=$DIR/cert.pem
ROOT_CNF=$DIR/ca-x509-extensions.cnf
CNF=$DIR/x509-extensions.cnf

mkdir -p $DIR

echo [$ROOT_CA_KEY] Generating private key for root CA...
openssl genpkey -algorithm RSA -out $ROOT_CA_KEY -pkeyopt rsa_keygen_bits:4096

echo [$ROOT_CA_CSR] Generating certificate request for root CA...
openssl req -new -key $ROOT_CA_KEY -days 5480 -extensions v3_ca -batch \
  -out $ROOT_CA_CSR -utf8 -subj '/C=GR/O=Synnefo/OU=SynnefoCloudSoftware'

echo [$ROOT_CA_CERT] Generating certificate for root CA...
openssl x509 -req -sha256 -days 3650 -in $ROOT_CA_CSR -signkey $ROOT_CA_KEY \
  -set_serial 1 -extfile $ROOT_CNF -out $ROOT_CA_CERT



echo [$KEY] Generating private key for services...
openssl genpkey -algorithm RSA -out $KEY -pkeyopt rsa_keygen_bits:2048

echo [$CSR] Generating certificate request for services...
openssl req -new -key $KEY -days 1096 -extensions v3_ca -batch \
  -out $CSR -utf8 -subj '/OU=SynnefoCloudServices/CN=%DOMAIN%'

echo [$CERT] Generating certificate for services...
openssl x509 -req -sha256 -days 1096 -in $CSR \
  -CAkey $ROOT_CA_KEY -CA $ROOT_CA_CERT -set_serial 100 \
  -out $CERT -extfile $CNF
