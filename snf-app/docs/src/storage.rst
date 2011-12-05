Storage guide
=============

Instructions for RADOS cluster deployment and administration

This document describes the basic steps to obtain a working RADOS cluster /
object store installation, to be used as a storage backend for synnefo, and
provides information about its administration.

It begins by providing general information on the RADOS object store describing
the different nodes in a RADOS cluster, and then moves to the installation and
setup of the distinct software components. Finally, it provides some basic
information about the cluster administration and debugging.

RADOS is the object storage component of the Ceph project
(http://http://ceph.newdream.net). For more documentation, see the official wiki
(http://ceph.newdream.net/wiki), and the official documentation
(http://ceph.newdream.net/docs). Usage information for userspace tools, used to
administer the cluster, are also available in the respective manpages.


RADOS Intro
-----------
RADOS is the object storage component of Ceph.

An object, in this context, means a named entity that has

 * name: a sequence of bytes, unique within its container, that is used to locate
   and access the object
 * content: sequence of bytes
 * metadata: a mapping from keys to values

RADOS takes care of distributing the objects across the whole storage cluster
and replicating them for fault tolerance.


Node types
----------

Nodes in a RADOS deployment belong in one of the following types:

 * Monitor:
   Lightweight daemon (ceph-mon) that provides a consensus for distributed
   decisionmaking in a Ceph/RADOS cluster. It also is the initial point of
   contact for new clients, and will hand out information about the topology of
   the cluster, such as the osdmap.

   You normally run 3 ceph-mon daemons, on 3 separate physical machines,
   isolated from each other; for example, in different racks or rows.  You could
   run just 1 instance, but that means giving up on high availability.

   Any decision requires the majority of the ceph-mon processes to be healthy
   and communicating with each other. For this reason, you never want an even
   number of ceph-mons; there is no unambiguous majority subgroup for an even
   number.

 * OSD:
   Storage daemon (ceph-osd) that provides the RADOS service. It uses the
   monitor servers for cluster membership, services object read/write/etc
   request from clients, and peers with other ceph-osds for data replication.

   The data model is fairly simple on this level. There are multiple named
   pools, and within each pool there are named objects, in a flat namespace (no
   directories). Each object has both data and metadata.

   By default, three pools are created (data, metadata, rbd).

   The data for an object is a single, potentially big, series of bytes.
   Additionally, the series may be sparse, it may have holes that contain binary
   zeros, and take up no actual storage.
   
   The metadata is an unordered set of key-value pairs. Its semantics are
   completely up to the client.

   Multiple OSDs can run on one node, one for each disk included in the object
   store. This might impose a perfomance overhead, due to peering/replication.
   Alternatively, disks can be pooled together (either with RAID or with btrfs),
   requiring only one osd to manage the pool.

   In the case of multiple OSDs, care must be taken to generate a CRUSH map,
   which doesn't replicate objects across OSDs on the same host (see the next
   section).

 * Clients:
   Clients that can access the RADOS cluster either directly, and on an object
   'granurality' by using librados and the rados userspace tool, or by using
   librbd, and the rbd tool, which creates an image / volume abstraction over
   the object store.

   RBD images are striped over the object store daemons, to provide higher
   throughput, and can be accessed either via the in-kernel Rados Block Device
   (RBD) driver, which maps RBD images to block devices, or directly via Qemu,
   and the Qemu-RBD driver.
   

Replication and Fault tolerance
-------------------------------

The objects in each pool are paritioned in a (per-pool configurable) number
of placement groups (pgs), and each placement group is mapped to a nubmer of
OSDs, according to the (per-pool configurable) replication level, and a
(per-pool configurable) CRUSH map, which defines how objects are replicated
across OSDs.

The CRUSH map is generated with hints from the config file (eg hostnames, racks
etc), so that the objects are replicated across OSDs in different 'failure
domains'. However, in order to be on the safe side, the CRUSH map should be
examined to verify that for example PGs are not replicated acroos OSDs on the
same host, and corrected if needed (see the Admin section).

Information about objects, pools, and pgs is included in the osdmap, which
the clients fetch initially from the monitor servers. Using the osdmap,
clients learn which OSD is the primary for each PG, and therefore know which
OSD to contact when they want to interact with a specific object. 

More information about the internals of the replication / fault tolerace /
peering inside the RADOS cluster can be found in the original RADOS paper
(http://dl.acm.org/citation.cfm?id=1374606).


Journaling
-----------

The OSD maintains a journal to help keep all on-disk data in a consistent state
while still keep write latency low. That is, each OSD normally has a back-end
file system (ideally btrfs) and a journal device or file.

When the journal is enabled, all writes are written both to the journal and to
the file system. This is somewhat similar to ext3's data=journal mode, with a
few differences. There are two basic journaling modes:

 * In writeahead mode, every write transaction is written first to the journal.
   Once that is safely on disk, we can ack the write and then apply it to the
   back-end file system. This will work with any file system (with a few
   caveats).
   
 * In parallel mode, every write transaction is written to the journal and the 
   file system in parallel. The write is acked when either one safely commits
   (usually the journal). This will only work on btrfs, as it relies on
   btrfs-specific snapshot ioctls to rollback to a consistent state before
   replaying the journal.


Authentication
--------------

Ceph supports cephx secure authentication between the nodes, this to make your
cluster more secure. There are some issues with the cephx authentication,
especially with clients (Qemu-RBD), and it complicates the cluster deployment.
Future revisions of this document will include documentation on setting up
fine-grained cephx authentication acroos the cluster.


RADOS Cluster design and configuration
--------------------------------------

This section proposes and describes a sample cluster configuration.

0. Monitor servers:
	* 3 mon servers on separate 'failure domains' (eg rack) 
	* Monitor servers are named mon.a, mon.b, mon.c repectively
	* Monitor data stored in /rados/mon.$id (should be created)
	* Monitor servers bind on 6789 TCP port, which should not be blocked by
	  firewall
	* Ceph configuration section for monitors:
		[mon]
			mon data = /rados/mon.$id

		[mon.a]
			host = [hostname] 
			mon addr = [ip]:6789
		[mon.b]
			host = [hostname] 
			mon addr = [ip]:6789
		[mon.c]
			host = [hostname] 
			mon addr = [ip]:6789
			
	* Debugging options which can be included in the monitor configuration:
		[mon] 
			;show monitor messaging traffic
			debug ms = 1 
			;show monitor debug messages
			debug mon = 20
			; show Paxos debug messages (consensus protocol)
			debug paxos = 20

1. OSD servers:
	* A numeric id is used to name the osds (osd.0, osd.1, ... , osd.n)
	* OSD servers bind on 6800+ TCP ports, which should not be blocked by
	  firewall
	* OSD data are stored in /rados/osd.$id (should be created and mounted if
	  needed)
	* /rados/osd.$id can be either a directory on the rootfs, or a separate
	  partition, on a dedicated fast disk (recommended)
		
	  The upstream recommended filesystem is btrfs. btrfs will use the parallel
	  mode for OSD journaling.

	  Alternatively, ext4 can be used. ext4 will use the writeahead mode for OSD
	  journaling. ext4 itself can also use an external journal device
	  (preferably a fast, eg SSD, disk). In that case, the filesystem can be
	  mounted with data=journal,commit=9999,noatime,nodiratime options, to
	  improve perfomance (proof?):

		mkfs.ext4 /dev/sdyy
	  	mke2fs -O journal_dev /dev/sdxx
		tune2fs -O ^has_journal /dev/sdyy
		tune2fs -o journal_data -j -J device=/dev/sdxx /dev/sdyy
		mount /dev/sdyy /rados/osd.$id -o noatime,nodiratime,data=journal,commit=9999
		
	* OSD journal can be either on a raw block device, a separate partition, or
	  a file.

	  A fash disk (SSD) is recommended as a journal device. 
	  
	  If a file is used, the journal size must be also specified in the
	  configuration.

	* Ceph configuration section for monitors:
		[osd]
			osd data = /rados/osd.$id
			osd journal = /dev/sdzz
			;if a file is used as a journal
			;osd journal size = N (in MB)
		
		[osd.0]
			;host and rack directives are used to generate a CRUSH map for PG
			;placement
			host = [hostname]
			rack = [rack]
			
			;public addr is the one the clients will use to contact the osd
			public_addr = [public ip]
			;cluster addr is the one used for osd-to-osd replication/peering etc
			cluster_addr = [cluster ip]

		[osd.1] 
			...

	* Debug options which can be included in the osd configuration:
		[osd]
			;show OSD messaging traffic
			debug ms = 1
			;show OSD debug information
			debug osd = 20
			;show OSD journal debug information
			debug jorunal = 20
			;show filestore debug information
			debug filestore = 20
			;show monitor client debug information
			debug monc = 20

3. Clients
	* Clients configuration only need the monitor servers addresses
	* Configration section for clients:
		[mon.a]
			mon addr = [ip]:6789
		[mon.b]
			mon addr = [ip]:6789
		[mon.c]
			mon addr = [ip]:6789
	* Debug options which can be included in the client configuration:
			;show client messaging traffic
			debug ms = 1
			;show RADOS debug information
			debug rados = 20
			;show objecter debug information
			debug objecter = 20
			;show filer debug information
			debug filer = 20
			;show objectcacher debug information
			debug object cacher = 20
		
4. Tips
	* Mount all the filesystems with noatime,nodiratime options
	* Even without any debug options, RADOS generates lots of logs. Make sure
	  the logs files are in a fast disk, with little I/O traffic, and the
	  partition is mounted with noatime.


Installation Process
--------------------

This section describes the installation process of the various software
components in a RADOS cluster.

0. Add Ceph Debian repository in /etc/apt/sources.list on every node (mon, osd,
   clients)::

	 deb http://ceph.newdream.net/debian/ squeeze main
	 deb-src http://ceph.newdream.net/debian/ squeeze main

1. Monitor and OSD servers:
	* Install the ceph package
	* Upgrade to an up-to-date kernel (>=3.x)
	* Edit the /etc/ceph/ceph.conf to include the mon and osd configuration
	  sections, shown previously.
	* Create the corresponding dirs in /rados (mon.$id and osd.$id)
	* (optionally) Format and mount the osd.$id patition in /rados/osd.$id
	* Make sure the journal device specified in the conf exists.
	* (optionally) Make sure everything is mounted with the noatime,nodiratime
	  options
	* Make sure monitor and osd servers can freely ssh to each other, using only
	  hostnames.
	* Create the object store: 
		mkcephfs -a -c /etc/ceph/ceph.conf
	* Start the servers:
		service ceph -a start
	* Verify that the object store is healthy, and running:
		ceph helth
		ceph -s

2. Clients:
	* Install the ceph-common package
	* Upgrade to an up-to-date kernel (>=3.x)
	* Install linux-headers for the new kernel
	* Check out the latest ceph-client git repo:
		git clone git://github.com/NewDreamNetwork/ceph-client.git
	* Copy the ncecessary ceph header file to linux-headers:
		cp -r ceph-client/include/linux/ceph/* /usr/src/linux-$(uname-r)/include/linux/ceph/
	* Build the modules:
		cd ~/ceph-client/net/ceph/
		make -C /usr/src/linux-headers-3.0.0-2-amd64/  M=$(pwd) libceph.ko
		cp Modules.symvers ../../drivers/block/
		cd ~/ceph-client/drivers/block/
		make -C /usr/src/linux-headers-3.0.0-2-amd64/  M=$(pwd) rbd.ko
	* Optionally, copy rbd.ko and libceph. ko to /lib/modules/
	* Load the modules:
		modprobe rbd


Administration Notes
--------------------

This section includes some notes on the RADOS cluster administration.

0. Starting / Stopping servers
	* service ceph -a start/stop (affects all the servers in the cluster)
	* service ceph start/stop osd (affects only the osds in the current node)
	* service ceph start/stop mon (affects only the mons in the current node)
	* service ceph start/stop osd.$id/mon.$id (affects only the specified node)

	* sevice ceph cleanlogs/cleanalllogs

1. Stop the cluster cleanly
	ceph stop

2. Increase the replication level for a given pool:
	ceph osd pool set $poolname size $size

   Note that increasing the replication level, the overhead for the replication
   will impact perfomance.

3. Adjust the number of placement groups per pool:
	ceph osd pool set $poolname pg_num $num
   
   The default number of pgs per pool is determined by the number of OSDs in the
   cluster, and the replication level of the pool (for 4 OSDs and replication
   size 2, the default value is 8). The default pools (data,metadata,rbd) are
   assigned 256 PGs.

   After the splitting is complete, the number of PGs in the system must be
   changed. Warning: this is not considered safe on PGs in use (with objects),
   and should be changed only when the PG is created, and before being used:
   ceph osd pool set $poolname pgp_num $num

4. Replacing the journal for osd.$id:
	Edit the osd.$id journal configration section
	ceph-osd -i osd.$id --mkjournal
	ceph-osd -i osd.$id --osd.journal /path/to/journal

5. Add a new OSD:
	Edit /etc/ceph/ceph.conf to include the new OSD
	ceph mon getmap -o /tmp/monmap
	ceph-osd --mkfs -i osd.$id --monmap /tmp/monmap
	ceph osd setmaxosd [maxosd+1] (ceph osd getmaxosd to get the num of osd if needed)
	service ceph start osd.$id

	Generate the CRUSH map to include the new osd in PGs:
		osdmaptool --createsimple [maxosd] --clobber /tmp/osdmap --export-crush /tmp/crush
		ceph osd setcrushmap -i /tmp/crush
	Or edit the CRUSH map by hand:
		ceph osd getcrushmap -o /tmp/crush
		crushmaptool -d /tmp/crush -o crushmap
		vim crushmap
		crushmaptool -c crushmap -o /tmp/crush
		ceph osd setcrushmap -i /tmp/crush

6. General ceph tool commands:
	* ceph mon stat (stat mon servers)
	* ceph mon getmap (get the monmap, use monmaptool to edit)
	* ceph osd dump (dump osdmap -> pool info, osd info)
	* ceph osd getmap (get osdmap -> use osdmaptool to edit)
	* ceph osd lspools
	* ceph osd stat (stat osd servers)
	* ceph ost tree (osd server info)
	* ceph pg dump/stat (show info about PGs)

7. rados userspace tool:

   The rados userspace tool (included in ceph-common package), uses librados to
   communicate with the object store.

	* rados mkpool [pool]
	* rados rmpool [pool]
	* rados df (show usage per pool)
	* rados lspools (list pools)
	* rados ls -p [pool] (list objects in [pool]
	* rados bench [secs] write|seq -t [concurrent operation]
	* rados import/export <pool> <dir> (import/export a local directory in a rados pool)

8. rbd userspace tool:
   
   The rbd userspace tool (included in ceph-commong package), uses librbd and
   librados to communicate with the object store. 

	* rbd ls -p [pool] (list RBD images in [pool], default pool = rbd) 
	* rbd info [pool] -p [pool]
	* rbd create [image] --size n (in MB)
	* rbd rm [image]
	* rbd export/import [dir] [image]
	* rbd cp/mv [image] [dest]
	* rbd resize [image]
	* rbd map [image] (map an RBD image to a block device using the in-kernel RBD driver)
	* rbd unmap /dev/rbdx (unmap an RBD device)
	* rbd showmapped

9. In-kernel RBD driver

   The in-kernel RBD driver can be used to map and ummap RBD images as block
   devices. Once mapped, they will appear as /dev/rbdX, and a symlink will be
   created in /dev/rbd/[poolname]/[imagename]:[bdev id].

   It also exports a sysfs interface, under /sys/bus/rbd/ which can be used to
   add / remove / list devices, although the rbd map/unmap/showmapped commands
   are preferred.
   
   The RBD module depends on the net/ceph/libceph module, which implements the
   communication with the object store in the kernel.

10. Qemu-RBD driver
	
	The Qemu-RBD driver can be used directly by Qemu-KVM to access RBD images as
	block devices inside VMs. It currently supports a feature not present in the
	in-kenrel RBD driver (writeback_window).

	It can be configured via libvirt, and the configuration looks like this:

    .. code-block:: xml

		<disk type='network' device='disk'>
		  <driver name='qemu' type='raw'/>
		  <source protocol='rbd' name='[pool]/[image]:rbd_writeback_window=8000000'/>
		  <target dev='vda' bus='virtio'/>
		</disk>

	Notae: it requires an up-to-date version of libvirt, plus a Qemu/KVM
	version, which is not included in Debian.

9. Logging and Debugging:
	For command-line tools (ceph, rados, rbd), you can specify debug options in
	the form of --debug-[component]=n, which will override the options in the
	config file. In order to get any output when using the cli debug options,
	you must also use --log-to-stderr.
		
		rados ls -p rbd --log-to-stderr --debug-ms=1 --debug-rados=20

	Ceph log files are located in /var/log/ceph/mon.$id and
	/var/log/ceph/osd.$id.
