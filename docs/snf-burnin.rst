.. _snf-burnin:

snf-burnin
^^^^^^^^^^

:ref:`snf-burnin <snf-burnin>` is an integration testing tool for a running
Synnefo deployment. It uses the Synnefo REST APIs to run test scenarios for the
following categories:

* :ref:`Authentication <unauthorizedtestcase>`
* :ref:`Images <imagestestcase>`
* :ref:`Flavors <flavorstestcase>`
* :ref:`Servers <serverstestcase>`
* :ref:`Network <networktestcase>`
* :ref:`Storage <pithostestcase>`


Usage
=====

**Example:**

::

  snf-burnin --token=TOKEN \
             --api=CYCLADES_URL
             --pithos=PITHOS_URL \
             --astakos=ASTAKOS_URL \
             --plankton=PLANKTON_URL \
             --plankton-user=PLANKTON_SYSTEM_USER \
             --image-id=IMAGE_ID \
             --log-folder=LOG_FOLDER

For more info

::

  snf-burnin --help

::

  Options:
  -h, --help            show this help message and exit
  --api=API             The API URI to use to reach the Synnefo API
  --plankton=PLANKTON   The API URI to use to reach the Plankton API
  --plankton-user=PLANKTON_USER
                        Owner of system images
  --pithos=PITHOS       The API URI to use to reach the Pithos API
  --astakos=ASTAKOS     The API URI to use to reach the Astakos API
  --token=TOKEN         The token to use for authentication to the API
  --nofailfast          Do not fail immediately if one of the tests fails
                        (EXPERIMENTAL)
  --no-ipv6             Disables ipv6 related tests
  --action-timeout=TIMEOUT
                        Wait SECONDS seconds for a server action to complete,
                        then the test is considered failed
  --build-warning=TIMEOUT
                        Warn if TIMEOUT seconds have passed and a build
                        operation is still pending
  --build-fail=BUILD_TIMEOUT
                        Fail the test if TIMEOUT seconds have passed and a
                        build operation is still incomplete
  --query-interval=INTERVAL
                        Query server status when requests are pending every
                        INTERVAL seconds
  --fanout=COUNT        Spawn up to COUNT child processes to execute in
                        parallel, essentially have up to COUNT server build
                        requests outstanding (EXPERIMENTAL)
  --force-flavor=FLAVOR ID
                        Force all server creations to use the specified FLAVOR
                        ID instead of a randomly chosen one, useful if disk
                        space is scarce
  --image-id=IMAGE ID   Test the specified image id, use 'all' to test all
                        available images (mandatory argument)
  --show-stale          Show stale servers from previous runs, whose name
                        starts with `snf-test-'
  --delete-stale        Delete stale servers from previous runs, whose name
                        starts with `snf-test-'
  --force-personality=PERSONALITY_PATH
                        Force a personality file injection.
                        File path required.
  --log-folder=LOG_FOLDER
                        Define the absolute path where the output
                        log is stored.
  -V, --verbose         Print detailed output about multiple processes
                        spawning
  --set-tests=TESTS     Set comma seperated tests for this run.
                        Available tests: auth, images, flavors,
                        servers, server_spawn,
                        network_spawn, pithos.
                        Default = all


Log files
=========

In each run, snf-burnin stores log files in the folder defined in the
--log-foler parameter, under the folder with the timestamp of the
snf-burnin-run and the image used for it. The name prefixes of the log
files are:

* details: Showing the complete log of snf-burnin run.
* error: Showing the testcases that encountered a runtime error.
* failed: Showing the testcases that encountered a failure.


Detailed description of testcases
=================================

.. _unauthorizedtestcase:

UnauthorizedTestCase
--------------------
* Test that trying to access without a valid token, fails

.. _imagestestcase:

ImagesTestCase
--------------
* Test image list actually returns images
* Test detailed image list has the same length as list
* Test detailed and simple image list contain the same names
* Test system images have unique names
* Test every image has specific metadata defined
* Download image from Pithos
* Upload and register image

.. _flavorstestcase:

FlavorsTestCase
---------------
* Test flavor list actually returns flavors
* Test detailed flavor list has the same length as list
* Test detailed and simple flavor list contain the same names
* Test flavors have unique names
* Test flavor names have correct format

.. _serverstestcase:

ServersTestCase
---------------
* Test simple and detailed server list have the same length
* Test simple and detailed servers have the same names

SpawnServerTestCase
-------------------
* Submit create server
* Test server is in BUILD state in server list
* Test server is in BUILD state in server details
* Change server metadata
* Verify the changed metadata are correct
* Verify server metadata are set based on image metadata
* Wait until server changes state to ACTIVE, and verify state
* Test if OOB server console works
* Test if server has IPv4
* Test if server has IPv6
* Test if server responds to ping on IPv4 address
* Test if server responds to ping on IPv6 address
* Submit shutdown request
* Verify server status is STOPPED
* Submit start request
* Test server status is ACTIVE
* Test if server responds to ping on IPv4 address (verify up and running)
* Test if server responds to ping on IPv6 address (verify up and running)
* Test SSH to server and verify hostname (IPv4)
* Test SSH to server and verify hostname (IPv6)
* Test RDP connection to server (only for Window Images) (IPv4)
* Test RDP connection to server (only for Window Images) (IPv6)
* Test file injection for personality enforcement
* Submit server delete request
* Test server becomes DELETED
* Test server is no longer in server list

.. _networktestcase:

NetworkTestCase
---------------
* Submit create server A request
* Test server A becomes ACTIVE
* Submit create server B request
* Test server B becomes ACTIVE
* Submit create private network request
* Submit connect VMs to private network
* Test if VMs are connected to network
* Submit reboot request to server A
* Test server A responds to ping on IPv4 address (verify up and running)
* Submit reboot request to server B
* Test server B responds to ping on IPv4 address (verify up and running)
* Connect via SSH and setup the new network interface in server A
* Connect via SSH and setup the new network interface in server B
* Connect via SSH to server A and test if server B responds to ping on IPv4 address
* Disconnect servers from network and verify the network details
* Send delete network request and verify that the network is deleted from the list
* Send request to delete servers and wait until they are actually deleted

.. _pithostestcase:

PithosTestCase
--------------
* Test container list is not empty
* Test containers have unique names
* Create a new container
* Upload simple file to newly created container
* Download file from Pithos and test it is the same with the one uploaded
* Remove created file and container from Pithos


Example scripts
===============

Under /snf-tools/conf you can find example scripts for automating snf-burnin
testing using cron.

* **snf-burnin-run.sh** runs snf-burnin with the given parameters, deletes
  stale instances (servers, networks) from old runs and delete logs older
  than a week. It aborts if snf-burnin runs for longer than expected.

* **snf-burnin-output.sh** checks for failed snf-burnin tests the last 30
  minutes in a given log folder. Exit status is 0 if no failures were
  encountered, else exit status is 1.
