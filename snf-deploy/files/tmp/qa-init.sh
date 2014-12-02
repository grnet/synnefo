apt-get install \
        gawk \
        automake \
        bridge-utils \
        cabal-install \
        fakeroot \
        fping \
        ghc \
        ghc-haddock \
        git \
        graphviz \
        hlint \
        hscolour \
        iproute \
        iputils-arping \
        libghc-attoparsec-dev \
        libcurl4-gnutls-dev \
        libghc-crypto-dev \
        libghc-curl-dev \
        libghc-haddock-dev \
        libghc-hinotify-dev \
        libghc-hslogger-dev \
        libghc-hunit-dev \
        libghc-json-dev \
        libghc-network-dev \
        libghc-parallel-dev \
        libghc-quickcheck2-dev \
        libghc-regex-pcre-dev \
        libghc-snap-server-dev \
        libghc-temporary-dev \
        libghc-test-framework-dev \
        libghc-test-framework-hunit-dev \
        libghc-test-framework-quickcheck2-dev \
        libghc-base64-bytestring-dev \
        libghc-text-dev \
        libcurl4-gnutls-dev \
        libghc-utf8-string-dev \
        libghc-vector-dev \
        libghc-comonad-transformers-dev \
        libpcre3-dev \
        libghc6-zlib-dev \
        libghc-lifted-base-dev \
        shelltestrunner \
        lvm2 \
        make \
        ndisc6 \
        openssl \
        pandoc \
        pep8 \
        pylint \
        python \
        python-bitarray \
        python-coverage \
        python-epydoc \
        python-ipaddr \
        python-openssl \
        python-pip \
        python-pycurl \
        python-pyinotify \
        python-pyparsing \
        python-setuptools \
        python-simplejson \
        python-sphinx \
        python-yaml \
        qemu-kvm \
        socat \
        ssh \
        vim \
        python-fdsend


cabal update
cabal install \
        json \
        network \
        parallel \
        utf8-string \
        curl \
        hslogger \
        Crypto \
        hinotify==0.3.2 \
        regex-pcre \
        vector \
        lifted-base==0.2.0.3 \
        lens==3.10 \
        base64-bytestring==1.0.0.1


# cluster is not initialized
if ! gnt-cluster getmaster; then

  mkdir -p /etc/ganeti
  mkdir -p /srv/ganeti/file-storage
  mkdir -p /srv/ganeti/shared-file-storage
  mkdir -p /var/lib/ganeti/rapi

  cat >> /etc/ganeti/file-storage-paths <<EOF
/srv/ganeti/file-storage
/srv/ganeti/shared-file-storage
EOF

  apt-get install drbd8-utils
  cat >> /etc/modprobe.d/drbd.conf <<EOF
options drbd  minor_count=255 usermode_helper=/bin/true
EOF

  cat >> /etc/modules <<EOF
vhost-net
drbd
EOF

  modprobe -v vhost-net
  modprobe -v drbd

  apt-get install -t wheezy-backports qemu-kvm

  apt-get install snf-image

  wget -4 http://cdn.synnefo.org/debian_base-7.0-x86_64.diskdump \
      -o /var/lib/snf-image/debian_base.diskdump

  touch /etc/ganeti/vnc-cluster-password

  cat >> /var/lib/ganeti/rapi/users <<EOF
ganeti-qa qa_example_passwd write
EOF

fi
