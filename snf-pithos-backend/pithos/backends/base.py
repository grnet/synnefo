# Copyright 2011-2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

# Default setting for new accounts.
DEFAULT_QUOTA = 0  # No quota.
DEFAULT_VERSIONING = 'auto'



class NotAllowedError(Exception):
    pass


class QuotaError(Exception):
    pass


class AccountExists(NameError):
    pass


class ContainerExists(NameError):
    pass


class AccountNotEmpty(IndexError):
    pass


class ContainerNotEmpty(IndexError):
    pass


class ItemNotExists(NameError):
    pass


class VersionNotExists(IndexError):
    pass


class BaseBackend(object):
    """Abstract backend class that serves as a reference for actual implementations.

    The purpose of the backend is to provide the necessary functions for handling data
    and metadata. It is responsible for the actual storage and retrieval of information.

    Note that the account level is always valid as it is checked from another subsystem.

    When not replacing metadata/groups/policy, keys with empty values should be deleted.

    The following variables should be available:
        'hash_algorithm': Suggested is 'sha256'

        'block_size': Suggested is 4MB

        'default_policy': A dictionary with default policy settings
    """

    def close(self):
        """Close the backend connection."""
        pass

    def list_accounts(self, user, marker=None, limit=10000):
        """Return a list of accounts the user can access.

        Parameters:
            'marker': Start list from the next item after 'marker'

            'limit': Number of containers to return
        """
        return []

    def get_account_meta(self, user, account, domain, until=None, include_user_defined=True):
        """Return a dictionary with the account metadata for the domain.

        The keys returned are all user-defined, except:
            'name': The account name

            'count': The number of containers (or 0)

            'bytes': The total data size (or 0)

            'modified': Last modification timestamp (overall)

            'until_timestamp': Last modification until the timestamp provided

        Raises:
            NotAllowedError: Operation not permitted
        """
        return {}

    def update_account_meta(self, user, account, domain, meta, replace=False):
        """Update the metadata associated with the account for the domain.

        Parameters:
            'domain': Metadata domain

            'meta': Dictionary with metadata to update

            'replace': Replace instead of update

        Raises:
            NotAllowedError: Operation not permitted
        """
        return

    def get_account_groups(self, user, account):
        """Return a dictionary with the user groups defined for this account.

        Raises:
            NotAllowedError: Operation not permitted
        """
        return {}

    def update_account_groups(self, user, account, groups, replace=False):
        """Update the groups associated with the account.

        Raises:
            NotAllowedError: Operation not permitted

            ValueError: Invalid data in groups
        """
        return

    def get_account_policy(self, user, account):
        """Return a dictionary with the account policy.

        The keys returned are:
            'quota': The maximum bytes allowed (default is 0 - unlimited)

            'versioning': Can be 'auto', 'manual' or 'none' (default is 'manual')

        Raises:
            NotAllowedError: Operation not permitted
        """
        return {}

    def update_account_policy(self, user, account, policy, replace=False):
        """Update the policy associated with the account.

        Raises:
            NotAllowedError: Operation not permitted

            ValueError: Invalid policy defined
        """
        return

    def put_account(self, user, account, policy={}):
        """Create a new account with the given name.

        Raises:
            NotAllowedError: Operation not permitted

            ValueError: Invalid policy defined
        """
        return

    def delete_account(self, user, account):
        """Delete the account with the given name.

        Raises:
            NotAllowedError: Operation not permitted

            AccountNotEmpty: Account is not empty
        """
        return

    def list_containers(self, user, account, marker=None, limit=10000, shared=False, until=None, public=False):
        """Return a list of container names existing under an account.

        Parameters:
            'marker': Start list from the next item after 'marker'

            'limit': Number of containers to return

            'shared': Only list containers with permissions set

            'public': Only list containers containing public objects


        Raises:
            NotAllowedError: Operation not permitted
        """
        return []

    def list_container_meta(self, user, account, container, domain, until=None):
        """Return a list with all the container's object meta keys for the domain.

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container does not exist
        """
        return []

    def get_container_meta(self, user, account, container, domain, until=None, include_user_defined=True):
        """Return a dictionary with the container metadata for the domain.

        The keys returned are all user-defined, except:
            'name': The container name

            'count': The number of objects

            'bytes': The total data size

            'modified': Last modification timestamp (overall)

            'until_timestamp': Last modification until the timestamp provided

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container does not exist
        """
        return {}

    def update_container_meta(self, user, account, container, domain, meta, replace=False):
        """Update the metadata associated with the container for the domain.

        Parameters:
            'domain': Metadata domain

            'meta': Dictionary with metadata to update

            'replace': Replace instead of update

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container does not exist
        """
        return

    def get_container_policy(self, user, account, container):
        """Return a dictionary with the container policy.

        The keys returned are:
            'quota': The maximum bytes allowed (default is 0 - unlimited)

            'versioning': Can be 'auto', 'manual' or 'none' (default is 'manual')

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container does not exist
        """
        return {}

    def update_container_policy(self, user, account, container, policy, replace=False):
        """Update the policy associated with the container.

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container does not exist

            ValueError: Invalid policy defined
        """
        return

    def put_container(self, user, account, container, policy={}, delimiter=None):
        """Create a new container with the given name.

        Parameters:
            'delimiter': If present deletes container contents instead of the container

        Raises:
            NotAllowedError: Operation not permitted

            ContainerExists: Container already exists

            ValueError: Invalid policy defined
        """
        return

    def delete_container(self, user, account, container, until=None):
        """Delete/purge the container with the given name.

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container does not exist

            ContainerNotEmpty: Container is not empty
        """
        return

    def list_objects(self, user, account, container, prefix='', delimiter=None, marker=None, limit=10000, virtual=True, domain=None, keys=[], shared=False, until=None, size_range=None, public=False):
        """Return a list of object (name, version_id) tuples existing under a container.

        Parameters:
            'prefix': List objects starting with 'prefix'

            'delimiter': Return unique names before 'delimiter' and after 'prefix'

            'marker': Start list from the next item after 'marker'

            'limit': Number of objects to return

            'virtual': If not set, the result will only include names starting
                       with 'prefix' and ending without a 'delimiter' or with
                       the first occurance of the 'delimiter' after 'prefix'.
                       If set, the result will include all names after 'prefix',
                       up to and including the 'delimiter' if it is found

            'domain': Metadata domain for keys

            'keys': Include objects that satisfy the key queries in the list.
                    Use 'key', '!key' for existence queries, 'key op value' for
                    value queries, where 'op' can be one of =, !=, <=, >=, <, >

            'shared': Only list objects with permissions set

            'size_range': Include objects with byte size in (from, to).
                          Use None to specify unlimited

            'public': Only list public objects


        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container does not exist
        """
        return []

    def list_object_meta(self, user, account, container, prefix='', delimiter=None, marker=None, limit=10000, virtual=True, domain=None, keys=[], shared=False, until=None, size_range=None):
        """Return a list of object metadata dicts existing under a container.

        Same parameters with list_objects. Returned dicts have no user-defined
        metadata and, if until is not None, a None 'modified' timestamp.

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container does not exist
        """
        return []

    def list_object_permissions(self, user, account, container, prefix=''):
        """Return a list of paths that enforce permissions under a container.

        Raises:
            NotAllowedError: Operation not permitted
        """
        return []

    def list_object_public(self, user, account, container, prefix=''):
        """Return a dict mapping paths to public ids for objects that are public under a container."""
        return {}

    def get_object_meta(self, user, account, container, name, domain, version=None, include_user_defined=True):
        """Return a dictionary with the object metadata for the domain.

        The keys returned are all user-defined, except:
            'name': The object name

            'bytes': The total data size

            'type': The content type

            'hash': The hashmap hash

            'modified': Last modification timestamp (overall)

            'modified_by': The user that committed the object (version requested)

            'version': The version identifier

            'version_timestamp': The version's modification timestamp

            'uuid': A unique identifier that persists data or metadata updates and renames

            'checksum': The MD5 sum of the object (may be empty)

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container/object does not exist

            VersionNotExists: Version does not exist
        """
        return {}

    def update_object_meta(self, user, account, container, name, domain, meta, replace=False):
        """Update the metadata associated with the object for the domain and return the new version.

        Parameters:
            'domain': Metadata domain

            'meta': Dictionary with metadata to update

            'replace': Replace instead of update

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container/object does not exist
        """
        return ''

    def get_object_permissions(self, user, account, container, name):
        """Return the action allowed on the object, the path
        from which the object gets its permissions from,
        along with a dictionary containing the permissions.

        The dictionary keys are (also used for defining the action):
            'read': The object is readable by the users/groups in the list

            'write': The object is writable by the users/groups in the list

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container/object does not exist
        """
        return {}

    def update_object_permissions(self, user, account, container, name, permissions):
        """Update (set) the permissions associated with the object.

        Parameters:
            'permissions': Dictionary with permissions to set

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container/object does not exist

            ValueError: Invalid users/groups in permissions
        """
        return

    def get_object_public(self, user, account, container, name):
        """Return the public id of the object if applicable.

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container/object does not exist
        """
        return None

    def update_object_public(self, user, account, container, name, public):
        """Update the public status of the object.

        Parameters:
            'public': Boolean value

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container/object does not exist
        """
        return

    def get_object_hashmap(self, user, account, container, name, version=None):
        """Return the object's size and a list with partial hashes.

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container/object does not exist

            VersionNotExists: Version does not exist
        """
        return 0, []

    def update_object_hashmap(self, user, account, container, name, size, type, hashmap, checksum, domain, meta={}, replace_meta=False, permissions=None):
        """Create/update an object with the specified size and partial hashes and return the new version.

        Parameters:
            'domain': Metadata domain

            'meta': Dictionary with metadata to change

            'replace_meta': Replace metadata instead of update

            'permissions': Updated object permissions

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container does not exist

            ValueError: Invalid users/groups in permissions

            QuotaError: Account or container quota exceeded
        """
        return ''

    def update_object_checksum(self, user, account, container, name, version, checksum):
        """Update an object's checksum."""
        return

    def copy_object(self, user, src_account, src_container, src_name, dest_account, dest_container, dest_name, type, domain, meta={}, replace_meta=False, permissions=None, src_version=None, delimiter=None):
        """Copy an object's data and metadata and return the new version.

        Parameters:
            'domain': Metadata domain

            'meta': Dictionary with metadata to change from source to destination

            'replace_meta': Replace metadata instead of update

            'permissions': New object permissions

            'src_version': Copy from the version provided

            'delimiter': Copy objects whose path starts with src_name + delimiter

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container/object does not exist

            VersionNotExists: Version does not exist

            ValueError: Invalid users/groups in permissions

            QuotaError: Account or container quota exceeded
        """
        return ''

    def move_object(self, user, src_account, src_container, src_name, dest_account, dest_container, dest_name, type, domain, meta={}, replace_meta=False, permissions=None, delimiter=None):
        """Move an object's data and metadata and return the new version.

        Parameters:
            'domain': Metadata domain

            'meta': Dictionary with metadata to change from source to destination

            'replace_meta': Replace metadata instead of update

            'permissions': New object permissions

            'delimiter': Move objects whose path starts with src_name + delimiter

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container/object does not exist

            ValueError: Invalid users/groups in permissions

            QuotaError: Account or container quota exceeded
        """
        return ''

    def delete_object(self, user, account, container, name, until=None, delimiter=None):
        """Delete/purge an object.

        Parameters:
            'delimiter': Delete objects whose path starting with name + delimiter

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container/object does not exist
        """
        return

    def list_versions(self, user, account, container, name):
        """Return a list of all (version, version_timestamp) tuples for an object.

        Raises:
            NotAllowedError: Operation not permitted
        """
        return []

    def get_uuid(self, user, uuid):
        """Return the (account, container, name) for the UUID given.

        Raises:
            NotAllowedError: Operation not permitted

            NameError: UUID does not exist
        """
        return None

    def get_public(self, user, public):
        """Return the (account, container, name) for the public id given.

        Raises:
            NotAllowedError: Operation not permitted

            NameError: Public id does not exist
        """
        return None

    def get_block(self, hash):
        """Return a block's data.

        Raises:
            ItemNotExists: Block does not exist
        """
        return ''

    def put_block(self, data):
        """Store a block and return the hash."""
        return 0

    def update_block(self, hash, data, offset=0):
        """Update a known block and return the hash.

        Raises:
            IndexError: Offset or data outside block limits
        """
        return 0
