apt-get install -y \
        autoconf \
        automake \
        bridge-utils \
        bridge-utils \
        build-essential \
        cabal-install \
        debhelper \
        fakeroot \
        fping \
        fping \
        ghc \
        ghc-haddock \
        git \
        git-email \
        graphviz \
        happy \
        hscolour \
        iproute \
        iproute \
        iputils-arping \
        iputils-arping \
        less \
        libghc-attoparsec-dev \
        libghc-base64-bytestring-dev \
        libghc-cabal-dev \
        libghc-crypto-dev \
        libghc-curl-dev \
        libghc-hinotify-dev \
        libghc-hslogger-dev \
        libghc-json-dev \
        libghc-lifted-base-dev \
        libghc-network-dev \
        libghc-parallel-dev \
        libghc-psqueue-dev \
        libghc-regex-pcre-dev \
        libghc-snap-server-dev \
        libghc-temporary-dev \
        libghc-test-framework-dev \
        libghc-test-framework-hunit-dev \
        libghc-test-framework-quickcheck2-dev \
        libghc-utf8-string-dev \
        libghc-vector-dev \
        libpcre3 \
        libpcre3-dev \
        locales \
        lvm2 \
        lvm2 \
        ndisc6 \
        ndisc6 \
        openssh-client \
        openssl \
        openssl \
        pandoc \
        pep8 \
        pylint \
        python-bitarray \
        python-coverage \
        python-dev \
        python-epydoc \
        python-epydoc \
        python-ipaddr \
        python-mock \
        python-mock \
        python-openssl \
        python-openssl \
        python-paramiko \
        python-pycurl \
        python-pyinotify \
        python-pyparsing \
        python-setuptools \
        python-simplejson \
        python-sphinx \
        python-yaml \
        qemu-utils \
        qemu-utils \
        quilt \
        rsync \
        shelltestrunner \
        socat \
        ssh \
        ssh \
        vim


easy_install \
        jsonpointer \
        jsonpatch \
        logilab-astng==0.24.1 \
        logilab-common==0.58.3 \
        mock==1.0.1 \
        pep8==1.3.3 \
        psutil \
        pylint==0.26.0 \
        pyinotify==0.9.4


cabal update
cabal install \
        'base64-bytestring>=1' \
        lens-3.10.2 \
        'lifted-base>=0.1.2' \
        'hlint>=1.9.12'

echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen

locale-gen

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
