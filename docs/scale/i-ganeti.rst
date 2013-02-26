.. _i-ganeti:

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

ganeti ||
:ref:`image <i-image>` ||
:ref:`gtools <i-gtools>` ||
:ref:`network <i-network>`


Ganeti Setup
~~~~~~~~~~~~

In ``ganeti`` nodes install GRNet specific Ganeti package and enable drbd:

.. code-block:: console

   # apt-get install python-bitarray
   # apt-get install snf-ganeti ganeti-htools
   # modprobe drbd minor_count=255 usermode_helper=/bin/true


The following apply to ``master`` node. Here we will create a Ganeti cluster with
all available ``ganeti`` nodes. Please note that Ganeti needs a pair of rsa/dsa keys
for the root user. If already exist in `/root/.ssh/` in all nodes then --no-ssh-init
can be used. In omitted then the existing files will be overriden. Upon node add
Ganeti will replace `/etc/ssh/ssh_host*` files with the master's ones:

.. code-block:: console

    # gnt-cluster init --enabled-hypervisors=kvm \
                       --vg-name=ganeti \
                       --nic-parameters link=br0,mode=bridged \
                       --master-netdev eth0 \
                       --default-iallocator hail \
                       --hypervisor-parameters kvm:kernel_path=,vnc_bind_address=0.0.0.0 \
                       --no-ssh-init --no-etc-hosts \
                       ganeti.example.com

    # gnt-cluster modify --disk-parameters=drbd:metavg=ganeti
    # gnt-group modify --disk-parameters=drbd:metavg=ganeti default

    # for n in node2 node3 node4 node5 node6; do
        gnt-node add --no-ssh-key-check --master-capable=yes --vm-capable=yes $n.example.com
      done

We need to add a rapi user to Ganeti so that Synnefo can talk with the backend:

.. code-block:: console

   # result=$(echo -n "synnefo:Ganeti Remote API:example_rapi_passw0rd" | openssl md5)
   # echo "synnefo {HA1} $result" >> /var/lib/ganeti/rapi/users
   # /etc/init.d/ganeti restart


Test your Setup:
++++++++++++++++

In master node run:

.. code-block:: console

   gnt-cluster info
   gnt-node list
   gnt-network list
   gnt-instance list
