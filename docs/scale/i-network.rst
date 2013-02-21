.. _i-network:

Synnefo
-------

:ref:`synnefo <i-synnefo>` ||
:ref:`ns <i-ns>` ||
:ref:`apt <i-apt>` ||
:ref:`mq <i-mq>` ||
:ref:`db <i-db>` ||
:ref:`gunicorn <i-gunicorn>` ||
:ref:`apache <i-apache>` ||
:ref:`webproject <i-webproject>` ||
:ref:`astakos <i-astakos>` ||
:ref:`qh <i-qh>` ||
:ref:`cms <i-cms>` ||
:ref:`pithos <i-pithos>` ||
:ref:`cyclades <i-cyclades>` ||
:ref:`kamaki <i-kamaki>` ||
:ref:`backends <i-backends>`

Backends
++++++++

:ref:`ganeti <i-ganeti>` ||
:ref:`image <i-image>` ||
:ref:`gtools <i-gtools>` ||
network

snf-network Setup
~~~~~~~~~~~~~~~~~

The following apply to ``ganeti`` nodes.


Install the corresponding package:

.. code-block:: console

   # apt-get install nfqueue-bindings-python=0.3+physindev-1
   # apt-get install snf-network
   # apt-get install nfdhcpd

In `/etc/snf-network/default` add:

.. code-block:: console

   MAC_MASK = ff:ff:f0:00:00:00

Edit `/etc/nfdhcpd/nfdhcpd.conf` to your preferances (DNS, IPv6) and add the
following iptables rules:

.. code-block:: console

    # iptables -t mangle -A PREROUTING -i br+ -p udp -m udp --dport 67 -j NFQUEUE --queue-num 42
    # iptables -t mangle -A PREROUTING -i tap+ -p udp -m udp --dport 67 -j NFQUEUE --queue-num 42
    # iptables -t mangle -A PREROUTING -i prv+ -p udp -m udp --dport 67 -j NFQUEUE --queue-num 42

    # ip6tables -t mangle -A PREROUTING -i br+ -p ipv6-icmp -m icmp6 --icmpv6-type 133 -j NFQUEUE --queue-num 43
    # ip6tables -t mangle -A PREROUTING -i br+ -p ipv6-icmp -m icmp6 --icmpv6-type 135 -j NFQUEUE --queue-num 44


In router node in case you have a NAT setup run:

.. code-block:: console

    # iptables -t nat -A POSTROUTING -s 10.0.1.0/24 -j MASQUERADE
    # ip addr add 10.0.1.1/24 dev eth1


Test your Setup:
++++++++++++++++

Create a VM inside the public network via UI or Ganeti and see if it has internet connectivity.
