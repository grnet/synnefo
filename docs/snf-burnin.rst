.. _snf-burnin:

snf-burnin
^^^^^^^^^^

:ref:`snf-burnin <snf-burnin>` is an integration testing tool for a running
Synnefo deployment. Using the Synnefo REST APIs, it simulates a real user and
tries to identify any bugs or performance issues by running a series of a tests.
The tests are devided into the following categories:

* :ref:`Authentication Tests <unauthorizedtestcase>`
* :ref:`Image Tests <imagestestcase>`
* :ref:`Flavor Tests <flavorstestcase>`
* :ref:`Server Tests <serverstestcase>`
* :ref:`Network Tests <networktestcase>`
* :ref:`Storage Tests <pithostestcase>`


Usage
=====

:ref:`snf-burnin <snf-burnin>` is a command line tool written in python. It
supports a number of command line options though which the user can change the
behaviour of the tests.

A typical usage of snf-burnin is:

::

  snf-burnin --token=USERS_SECRET_TOKEN \
             --auth-url="https://accounts.synnefo.org/identity/v2.0/" \
             --system-images-user=SYSTEM_IMAGES_USER_ID \
             --image-id=IMAGE_ID \
             --log-folder=LOG_FOLDER

The above options are the minimal ones (mandatory) that one has to speficy in
order for snf-burnin to properly function. The first two are the credentials
needed to access Synnefo's REST API and can be found in the user's dashboard.
The third is needed by some :ref:`Image Tests <imagestestcase>` as we will see
later. The forth tells snf-burnin which image to use for creating our test
servers and the last one specifies the log folder where any results should be
saves.

For more information about snf-burnin and it's command line options, run
snf-burnin with help.

::

  Usage: snf-burnin [options]

  snf-burnin runs a number of test scenarios on a Synnefo deployment.

  Options:
    -h, --help            show this help message and exit
    --auth-url=AUTH_URL   The AUTH URI to use to reach the Synnefo API
    --system-images-user=SYSTEM_IMAGES_USER
                          Owner of system images
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

In each run, snf-burnin stores log files under the folder defined in the
--log-folder parameter. For every run, it creates a new subfolder using a
timestamp and the image-id as unique names. The name prefixes of the log files
are:

* details: Showing the complete log of snf-burnin run.
* error: Showing the testcases that encountered a runtime error.
* failed: Showing the testcases that encountered a failure.


Detailed description of testcases
=================================

Here we have a complete list of all the tests snf-burnin performs, each listed
under the category in which it belongs. The user can choose to run some or all
of the categories listed below using the "--set-tests" command line flag.


.. _unauthorizedtestcase:

UnauthorizedTestCase
--------------------
* Use a random token and try to authenticate to Astakos service. The expected
  responce should be "401 Unauthorized".

.. _imagestestcase:

ImagesTestCase
--------------
* Request from Cyclades the list of all registered images and check that its
  length is greater than 0 (ie test that there are registered images for the
  users to use).
* Request from Cyclades the list of all registered images with details and check
  that is length is greater than 0.
* Test that the two lists retrieved earlier contain exactly the same images.
* Using the SYSTEM_IMAGES_USER_ID choose only the images that belong to the
  system user and check that their names are unique. This test can not be
  applied for all images as the users can name their images whatever they want.
* Again for the images that belong to the system user check that the "osfamily"
  and the "root_partition" metadata values have been defined. These metadata
  values are mandatory for an image to be used.
* Download from Pithos+ the image specified with the "--image-id" parameter and
  save it locally.
* Create a new container to Pithos+ named "images".
* Upload the download image to Pithos+ under the "images" container.
* Use Plankton service to register the above image. Set the "osfamily" and
  "root_partition" metadata values which are mandatory.
* Request from Cyclades the list of all registered images and check that our
  newly registered image is among them.
* Delete image from Pithos+ and also the local copy on our disk.

.. _flavorstestcase:

FlavorsTestCase
---------------
* Request from Cyclades the list of all flavors and check that its length is
  greater than 0 (ie test that there are flavors for the users to use).
* Request from Cyclades the list of all flavors with details and check that its
  length is greater than 0.
* Test that the two lists retrived earlier contain exactly the same flavors.
* Test that all flavors have unique names.
* Test that all flavors have a name of the form CxxRyyDzz where xx is the vCPU
  count, yy is the RAM in MiB, and zz is the Disk in GiB.

.. _serverstestcase:

ServersTestCase
---------------
* Request from Cyclades the list of all servers with and without details and
  check that the two lists have the same length.
* Test that simple and detailed servers lists have the same names.

SpawnServerTestCase
-------------------
* Submit a create server request to Cyclades service. Use the IMAGE_ID specified
  from the command line. If FLAVOR_ID was specified as well use that one, else
  choose one randomly. The name of the new server will start with "snf-test-"
  followed by a timestamp so we can know which servers have been created from
  snf-burnin and when. Also check that the response from Cyclades service
  contains the correct server_name, server_flavor_id, server_image_id and the
  status of the server is currenlty "BUILD". Finally from the above response,
  extract the server's id and password.
* Request from Cyclades the list of all servers with details and check that our
  newly created server has correct server_name, server_flavor_id,
  server_image_id and the status is "BUILD".
* Request from Cyclades the details from the image we used to build our server.
  Extract the "os" and "users" metadata values. Using the first one update the
  server's metadata and setup the "os" metadata value to be the same with the
  one from the image's metadata. Using the second one determine the username to
  use for future connections to this host.
* Retrieve the server's metadata from Cyclades and verify that server's metadata
  "os" key is set based on image's metadata.
* Wait until server changes state to ACTIVE. This is done by querying the
  service for the server's state every QUERY_INTERVAL period of time until
  BUILD_TIMEOUT has been reached. Both QUERY_INTERVAL and BUILD_TIMEOUT values
  can be changed from the command line.
* Request from Cyclades service a VNC console to our server. In order to verify
  that the returned connection is indeed a VNC one, snf-burnin implements the
  first basic steps of the RFB protocol:
    * Step 1. Send the ProtocolVersion message (par. 6.1.1)
    * Step 2. Check that only VNC Authentication is supported (par 6.1.2)
    * Step 3. Request VNC Authentication (par 6.1.2)
    * Step 4. Receive Challenge (par 6.2.2)
    * Step 5. DES-Encrypt challenge, using the password as key (par 6.2.2)
    * Step 6. Check that the SecurityResult is correct (par 6.1.3)
* Request from Cyclades the server's details and check that our server's has
  been assigned with an IPv4 address.
* Check that our server has been assigned with an IPv6 address. This test can be
  skipped if for some reason the targeted Synnefo deployment doesn't support
  IPv6.
* Test that our server responds to ping requests on IPv4 address.
* Test that our server responds to ping requests on IPv6 address. This test can
  also be skipped.
* Submit a shutdown request for our server.
* Wait and verify that the status of our server became "STOPPED".
* Submit a start request for our server.
* Wait and verify that the status of our server became "ACTIVE" again.
* Test if server responds to ping on IPv4 address (verify up and running).
* Test if server responds to ping on IPv6 address (verify up and running).
* If the server is a Linux machine, SSH to it using its IPv4 address and verify
  that it has a valid hostname.
* If the server is a Linux machine, SSH to it using its IPv6 address and verify
  that it has a valid hostname.
* If the server is a Windows machine, try to connect to its RDP port using both
  its IPv4 and IPv6 addresses.
* If during the creation of the server, the user chose a personality file to be
  used, check that this file is been presented in the server and its contents
  are correct.
* Submit server delete request.
* Wait and verify that the status of our server became "DELETED".
* Request from Cyclades the list of all servers and verify that our newly
  deleted server is not in the list.

.. _networktestcase:

NetworkTestCase
---------------
* Submit create server A request.
* Wait and verify that the status of our A server became "ACTIVE".
* Submit create server B request.
* Wait and verify that the status of our B server became "ACTIVE".
* Submit create private network request. Wait and verify that the status of the
  network became "ACTIVE".
* Connect the two servers (A and B) into the newly created network. Wait and
  verify that both machines got an extra nic, hence have been connected to the
  network.
* Reboot server A.
* Test if server A responds to ping on IPv4 address (verify up and running)
* Reboot server B.
* Test if server B responds to ping on IPv4 address (verify up and running)
* Connect via SSH and setup the new network interface in server A.
* Connect via SSH and setup the new network interface in server B.
* Connect via SSH to server A and test if server B responds to ping via their
  new interface.
* Disconnect both servers from network. Check network details and verify that
  both servers have been successfully disconnected.
* Send delete network request. Verify that the network has been actually
  deleted.
* Send request to delete servers and wait until they are actually deleted.

.. _pithostestcase:

PithosTestCase
--------------
* Request from Pithos+ the list of containers and check that its length is
  greater than 0 (ie test that there are containers).
* Test that the containers have unique names.
* Create a new container. Choose a random name for our container and then check
  that it has been successfully created.
* Upload a file to Pithos+ under our newly created container.
* Download the file from Pithos+ and test it is the same with the one uploaded.
* Remove created file and container from Pithos+ and verify that they have been
  successfully deleted.


Burnin as alert tool
========================

Burnin can be used to verify that a Synnefo deployment is working as expected
and verify the admins in case of an error. For this there is a script under the
/snf-tools/conf directory named **snf-burnin-run.sh** which is intended to be
used from cron to periodically run burnin. It runs simultaneous many instances
of burnin for a number of different users and report errors though email.
