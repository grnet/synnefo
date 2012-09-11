snf-burnin documentation
=========================

**snf-burnin** is an integration testing tool for a running Synnefo deployment. It runs test scenarios from the following categories:

* Authentication 
* Images
* Flavors
* Servers
* Networking

.. toctree::
   :maxdepth: 2

Usage
=====
**Example:**

::

   snf-burnin --api=API_URL --token=TOKEN --image-id=IMAGE-ID --log-folder=LOG_FOLDER --plankton=PLANKTON_API --plankton-user=PLANKTON_SYSTEM_USER

For more info 

::


   snf-burnin --help

::


  Options:
  
  -h, --help                        show this help message and exit
  --api=API             	    The API URI to use to reach the Synnefo API
  --plankton=PLANKTON   	    The API URI to use to reach the Plankton API
  --plankton-user=PLANKTON_USER	    Owner of system images
  --token=TOKEN                     The token to use for authentication to the API
  --nofailfast          	    Do not fail immediately if one of the tests fails (EXPERIMENTAL)
  --no-ipv6             	    Disables ipv6 related tests
  --action-timeout=TIMEOUT	    Wait SECONDS seconds for a server action to complete, then the test is considered failed
  --build-warning=TIMEOUT           Warn if TIMEOUT seconds have passed and a build operation is still pending
  --build-fail=BUILD_TIMEOUT  	    Fail the test if TIMEOUT seconds have passed and a build operation is still incomplete
  --query-interval=INTERVAL 	    Query server status when requests are pending every INTERVAL seconds
  --fanout=COUNT             	    Spawn up to COUNT child processes to execute in parallel, essentially have up to COUNT server build requests outstanding (EXPERIMENTAL)
  --force-flavor=FLAVOR ID	    Force all server creations to use the specified FLAVOR ID instead of a randomly chosen one, useful if disk space is scarce 
  --image-id=IMAGE ID               Test the specified image id, use 'all' to test all available images (mandatory argument)
  --show-stale          	    Show stale servers from previous runs, whose name starts with `snf-test-'
  --delete-stale        	    Delete stale servers from previous runs, whose name starts with `snf-test-'
  --force-personality=PERSONALITY_PATH
                                    Force a personality file injection. File path required.
  --log-folder=LOG_FOLDER           Define the absolute path where the output log is stored.




Detailed description of testcases
=================================

ImagesTestCase
---------------
* Test image list actually returns images
* Test detailed image list actually returns images
* Test simple and detailed image lists have the same length
* Test simple and detailed images have the same names
* Test system images have the same name
* Test system images have unique names
* Test every image has specific metadata

FlavorsTestCase
----------------
* Test flavor list actually returns flavors
* Test simple and detailed flavor lists have the same length
* Test simple and detailed flavors have the same names
* Test flavors have unique names
* Test flavor names have correct format 

ServersTestCase
----------------
* Test simple and detailed server list have the same length
* Test simple and detailed servers have the same names

SpawnServerTestcase
--------------------
* Submit create server
* Test server is in BUILD state in server list
* Test server is in BUILD state in details
* Change server metadata
* Verify the changed metadata are correct
* Verify server metadata are set based on image metadata
* Wait until server change state to ACTIVE, and verify state
* Test if OOB server console works
* Test server has IPv4
* Test server has IPv6
* Test server responds to ping on IPv4 address
* Test server responds to ping on IPv6 address
* Submit shutdown request
* Verify server status is STOPPED
* Submit start request 
* Test server status is ACTIVE
* Test server responds to ping on IPv4 address (verify if is actually up and running)
* Test server responds to ping on IPv6 address (verify if is actually up and running)
* Test SSH to server and verify hostname (IPv4)
* Test SSH to server and verify hostname (IPv6)
* Test RDP connection to server (only available to Windows Images) (IPv4)
* Test RDP connection to server (only available to Windows Images) (IPv6)
* Test file injection for personality enforcement
* Submit server delete request
* Test server becomes DELETED
* Test server is no longer in server list

NetworkTestCase
===============
* Submit create server A request
* Test server A becomes ACTIVE
* Submit create server B request
* Test server B becomes ACTIVE
* Submit create private network request
* Connect VMs to private network
* Test if VMs are connected to network
* Submit reboot request to server A
* Test server A responds to ping on IPv4 address (verify if is actually up and running)
* Submit reboot request to server B
* Test server B responds to ping on IPv4 address (verify if is actually up and running)
* Connect via SSH and setup the new network interface in server A
* Connect via SSH and setup the new network interface in server B
* Connect via SSH to server A and test if server B responds to ping on IPv4 address
* Disconnect servers from network and verify the network details
* Send delete network request and verify that the network is deleted from the list
* Send request to delete servers and wait until they are actually deleted




Indices and tables
==================

* :ref:`genindex`
* :ref:`search`

