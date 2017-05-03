================================
Rescue Mode for Virtual Machines
================================


Abstract
========

Enable rescue mode in VMs in order to repair a machine with a corrupted state.

Current state and shortcomings
==============================

There are some cases where a user wants to have access to their file system
without having access to the operating system either because it is rendered
unavailable or because they lost access to it(e.g. forgot their password). In
that case the Machine is considered useless.

Proposed changes
================

Cyclades should be extended in a way that will enable users to boot their VMs
with a temporary "rescue" image which will give them certain level of access to
a VM in a broken state. This change should give the option to start the VM in
rescue mode, perform operations, revert the rescue state and finally startup
the instance with the updates performed.

The rescue functionality will initially be implemented by modifying the ganeti
instance and adding the path of the rescue image as a cdrom and also changing
the boot order. In that way, while the VM is in rescue mode, it will boot from
the rescue image.

In order to support rescue images we need to create a new kind of image in the
database that will act as the rescue image placeholder. As a starting point we
will have to assume that the file of this image will be stored in the machine
hosting the VM and will be accessible through a UNIX path
(e.g., /path/to/myimage.iso). As a future step, we can make these images
accessible from Pithos.

Finally we need to implement the respective API endpoints as well as management
commands to support this rescue/unrescue functionality.

Rescue Images
^^^^^^^^^^^^^

Considering the described implementation, there should exist some images that
will enable the underlying functionality. Such images are available in public
for various Operating Systems but we have to consider which one to use in each
case. A straightforward approach is to define a correlation between the images
that are used to instantiate a VM and a respective rescue image.

This can be done by creating a new `RescueImage` model that will consist of the
filename of the image as well as some properties (e.g. OS Family, OS etc) which
will be used to determine which image to use in each case.

In order to support these images, we need to create management commands that
will perform CRUD operations. The next section will analyze the different type
of operations and the caveats that will be introduced.

Rescue Image Creation
---------------------

The creation of the rescue image should require that the image file is placed
under a certain directory that will be defined in the cyclades settings and
therefore, its **filename will be unique**. The user that creates this image
should provide the name of the image, its properties and optionally they can
make it default, in the sense that the system will select it when there is no
other better alternative.

Rescue Image Information/Listing
--------------------------------

Along with the properties described above, the listing should also provide
information about the VMs that are currently on rescue mode and are using this
image. That functionality is helpful when an administrator wants to seamlessly
delete an image. In order to do that, we need to add an extra field on the
VirtualMachine model that will be a foreign key to the RescueImage model.

Rescue Image Deletion
---------------------

As mentioned above, an image should be available for deletion when no VMs are
using it while being in rescue mode. The image will not be deleted from the
database but will rather be marked as deleted using a `deleted` flag on the
model.

Rescue Image Update
-------------------

In a similar manner to creating a Rescue Image, an update could change the
properties of the image, its name and the default flag.

Some scenarios that should be taken into consideration:

1. A VM is migrated to different node.

   Given the proposed implementation, as long as the HTTP URL works, the VM,
   will work seamlessly after a migration.

2. An administrator wants to delete a rescue image that is currently being
   used by a VM in rescue mode.

   The management commands will provide a reliable administrative interface
   that will ensure a rescue image is deleted seamlessly. In order to achieve
   that the system should count the number of VMs using an image and behave
   accordingly.

3. An administrator wants to delete an image and user has currently issued a
   rescue command.

   In order to resolve this race condition we should define when a rescue image
   is considered *in use*. Since a rescue command, issues an asynchronous RAPI
   call, there is no way to know when this will be finished. The system will
   assume that an image for which the following is true,

   `vm.rescue = True or (vm.rescue = False and vm.action = 'RESCUE')`

   is currently in use and therefore cannot be deleted.

4. The result of the SET_INSTANCE_PARAMS after a rescue operation is not
   processed by cyclades

   Since similarly to the resize operation, the VM will end up in an unsynced
   state that can only be fixed through reconciliation.

Implementation details
======================

The implementation will follow the following steps:

Regarding the VirtualMachine model:

* Add an extra `rescue` BooleanField on the VirtualMachine Model state
* Add an extra `rescue_image` foreign key on the VirtualMachine Model. This
  will be assigned when a VM goes into rescue mode.

* Add 2 extra actions on the VirtualMachine Model:

  1) `RESCUE`: This action should transition a VM that is shutoff into rescue
     state. The operation state (STOPPED) should not change. Upon successful
     execution, the dispatcher should detect that a VM has a rescue image
     attached and should set the `rescue` flag to `true`.

  2) `UNRESCUE`: This action should transition a VM that is shutoff and has
     the `rescue` flag set to `true`, into its initial state. In the same
     manner as (1), upon successful execution the dispatcher should set the
     `rescue` flag to `false`.

Regarding the Image/RescueImage model:

* Create `RescueImage` model. This model should hold attributes of the image
  such as the OS family, the OS etc. The system will support only 2 types of
  images in the first iteration. HTTP and plain files placed in VM capable
  nodes.
* Add a utility method which will calculate the number of VMs using a specific
  rescue image. This should be done using the count aggregate function.

Regarding the Cyclades API

* Add 2 extra actions on the `/servers/{server-id}/action` cyclades API
  endpoint:

  1) `rescue`:  This action should accept a user provided `rescue_image_ref`.
	  In case it is not provided, the system should select an appropriate one.
  2) `unrescue`: This action shouldn't take any parameters.

Regarding the logic:

* Extend `validate_server_action` function to perform sanity checks for the
  rescue/unrescue commands. A `rescue` action upon a VM that is not shutoff,
  should fail. Similarly, `unrescue` action should fail if the VM is not
  shutoff and the `rescue` flag is not True.

* Add the following `server_command` s:

  1) `RESCUE`: This command should obtain the rescue image from a utility
      method in `snf-cyclades-app/synnefo/api/util.py` and propagate the call
      to the backend.
  2) `UNRESCUE`: This command should just propagate the action to the backend.

* Add the following functions to backend:
  1) `rescue_instance` This function should build the `hvparams` (hypervisor
  parameters that will be send to Ganeti) and issue an OP_INSTANCE_MODIFY call.
  The hypervisor parameters should be the `cdrom_image_path` that will contain
  the path to the rescue image, as well as the `boot_order` set to
  "cdrom,disk".
  2) `unrescue_instance` This function should just reset the `hvparams` to the
  original state and make an InstanceModify RAPI call.

Regarding the dispatcher:

* Extend the `process_op_status` to handle rescue and unrescue actions. A
  rescue action is basically an Instance Modification with specific `hvparams`.
  In case the dispatcher identifies such an action, it should set the rescue
  flag of the VM to true. In other case the dispatcher should set  `rescue_image`
  field to None. In a similar manner, a successful unrescue action should set the
  vm `rescue` flag to False.

Regarding the reconciliation:

* Extend the reconciliation functionality to identify servers that are on
  rescue mode in Ganeti but not in cyclades and vise-versa. With the assumption
  that Ganeti always holds the correct state, cyclades should sync their state
  to the respective Ganeti one.

Regarding the Managment Commands:

*  `snf-manage server-modify --action rescue --rescue-image <image-id>`
   Rescue a server

*  `snf-manage server-modify --action unrescue`
   Unrescue a server

*  `snf-manage rescue-image-add --name <name>
                          --location <location>
                          --location-type <file|http>
                          --os <os>
						  --target-os <target-os>
						  --target-os-family <target-os-family>
                          --os-family <os-family>
                          --default True|False`
*  `snf-manage rescue-image-modify
        <rescue-image-id> --name <name> --image-id <image-id>
                          --location <location>
                          --location-type <file|http>
                          --os <os>
						  --target-os <target-os>
						  --target-os-family <target-os-family>
                          --os-family <os-family>
                          --default True|False`
*  `snf-manage rescue-image-list`
*  `snf-manage rescue-image-remove <rescue-image-id>`
