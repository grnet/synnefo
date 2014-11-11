# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Default setting for new accounts.
DEFAULT_ACCOUNT_QUOTA = 0  # No quota.
DEFAULT_CONTAINER_QUOTA = 0  # No quota.
DEFAULT_CONTAINER_VERSIONING = 'auto'

(MAP_ERROR, MAP_UNAVAILABLE, MAP_AVAILABLE) = range(-1, 2)

class NotAllowedError(Exception):
    pass


class IllegalOperationError(NotAllowedError):
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


class InvalidHash(TypeError):
    pass


class InconsistentContentSize(ValueError):
    pass


class InvalidPolicy(ValueError):
    pass


class LimitExceeded(Exception):
    pass


class BrokenSnapshot(Exception):
    pass

class BaseBackend(object):
    """Abstract backend class.

    This class serves as a reference for actual implementations.

    The purpose of the backend is to provide the necessary functions
    for handling data and metadata.

    It is responsible for the actual storage and retrieval of information.

    Note that the account level is always valid as it is checked
    from another subsystem.

    When not replacing metadata/groups/policy, keys with empty values
    should be deleted.

    The following variables should be available:
        'hash_algorithm': Suggested is 'sha256'

        'block_size': Suggested is 4MB

        'default_account_policy': A dictionary with default account policy
                                  settings
        'default_container_policy': A dictionary with default container policy
                                    settings
    """

    def close(self):
        """Close the backend connection."""
        pass

    def list_accounts(self, user, marker=None, limit=10000):
        """Return a list of accounts the user can access.

        Keyword arguments:
            'marker': Start list from the next item after 'marker'

            'limit': Number of containers to return
        """
        return []

    def get_account_meta(self, user, account, domain=None, until=None,
                         include_user_defined=True):
        """Return a dictionary with the account metadata for the domain.

        The keys returned are all user-defined, except:
            'name': The account name

            'count': The number of containers (or 0)

            'bytes': The total data size (or 0)

            'modified': Last modification timestamp (overall)

            'until_timestamp': Last modification until the timestamp provided

        Raises:
            NotAllowedError: Operation not permitted

            ValueError: if domain is None and include_user_defined==True
        """
        return {}

    def update_account_meta(self, user, account, domain, meta, replace=False):
        """Update the metadata associated with the account for the domain.

        Parameters:
            'domain': Metadata domain

        Keyword arguments:
            'meta': Dictionary with metadata to update

            'replace': Replace instead of update

        Raises:
            NotAllowedError: Operation not permitted
            LimitExceeded: if the metadata number exceeds the allowed limit.
        """
        return

    def get_account_groups(self, user, account):
        """Return a dictionary with the user groups defined for the account.

        Raises:
            NotAllowedError: Operation not permitted
        """
        return {}

    def update_account_groups(self, user, account, groups, replace=False):
        """Update the groups associated with the account.

        Raises:
            NotAllowedError: Operation not permitted

            ValueError: Invalid data in groups

            LimitExceeded: if the group number exceeds the allowed limit.
        """
        return

    def get_account_policy(self, user, account):
        """Return a dictionary with the account policy.

        The keys returned are:
            'quota': The maximum bytes allowed (default is 0 - unlimited)

            'versioning': Can be 'auto', 'manual' or 'none' (default: 'manual')

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

    def put_account(self, user, account, policy=None):
        """Create a new account with the given name.

        Raises:
            NotAllowedError: Operation not permitted

            InvalidPolicy: Invalid policy defined
        """
        return

    def delete_account(self, user, account):
        """Delete the account with the given name.

        Raises:
            NotAllowedError: Operation not permitted

            AccountNotEmpty: Account is not empty
        """
        return

    def list_containers(self, user, account, marker=None, limit=10000,
                        shared=False, until=None, public=False):
        """Return a list of container names existing under an account.

        Keyword arguments:
            'marker': Start list from the next item after 'marker'

            'limit': Number of containers to return

            'shared': Only list containers with permissions set

            'public': Only list containers containing public objects


        Raises:
            NotAllowedError: Operation not permitted
        """
        return []

    def list_container_meta(self, user, account, container, domain,
                            until=None):
        """Return a list of the container's object meta keys for a domain.

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container does not exist
        """
        return []

    def get_container_meta(self, user, account, container, domain=None,
                           until=None,
                           include_user_defined=True):
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

            ValueError: if domain is None and include_user_defined==True
        """
        return {}

    def update_container_meta(self, user, account, container, domain, meta,
                              replace=False):
        """Update the metadata associated with the container for the domain.

        Parameters:
            'domain': Metadata domain

        Keyword arguments:
            'meta': Dictionary with metadata to update

            'replace': Replace instead of update

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container does not exist

            LimitExceeded: if the metadata number exceeds the allowed limit.
        """
        return

    def get_container_policy(self, user, account, container):
        """Return a dictionary with the container policy.

        The keys returned are:
            'quota': The maximum bytes allowed (default is 0 - unlimited)

            'versioning': Can be 'auto', 'manual' or 'none' (default: 'manual')

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container does not exist
        """
        return {}

    def update_container_policy(self, user, account, container, policy,
                                replace=False):
        """Update the policy associated with the container.

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container does not exist

            InvalidPolicy: Invalid policy defined
        """
        return

    def put_container(self, user, account, container, policy=None):
        """Create a new container with the given name.

        Raises:
            NotAllowedError: Operation not permitted

            ContainerExists: Container already exists

            InvalidPolicy: Invalid policy defined
        """
        return

    def delete_container(self, user, account, container, until=None,
                         delimiter=None):
        """Delete/purge the container with the given name.

        Keyword arguments:
            'delimiter': If not None, deletes the container contents starting
                         with the delimiter

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container does not exist

            ContainerNotEmpty: Container is not empty
        """
        return

    def list_objects(self, user, account, container, prefix='', delimiter=None,
                     marker=None, limit=10000, virtual=True, domain=None,
                     keys=None, shared=False, until=None, size_range=None,
                     public=False):
        """List (object name, object version_id) under a container.

        Keyword arguments:
            'prefix': List objects starting with 'prefix'

            'delimiter': Return unique names before 'delimiter' and
                         after 'prefix'

            'marker': Start list from the next item after 'marker'

            'limit': Number of objects to return

            'virtual': If not set, the result will only include names starting
                       with 'prefix' and ending without a 'delimiter' or with
                       the first occurance of the 'delimiter' after 'prefix'.
                       If set, the result will include all names after 'prefix'
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

    def list_object_meta(self, user, account, container, prefix='',
                         delimiter=None, marker=None, limit=10000,
                         virtual=True, domain=None, keys=None, shared=False,
                         until=None, size_range=None, public=False):
        """Return a list of metadata dicts of objects under a container.

        Same parameters with list_objects. Returned dicts have no user-defined
        metadata and, if until is not None, a None 'modified' timestamp.

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container does not exist
        """
        return []

    def list_object_permissions(self, user, account, container, prefix=''):
        """Return a list of paths enforce permissions under a container.

        Raises:
            NotAllowedError: Operation not permitted
        """
        return []

    def list_object_public(self, user, account, container, prefix=''):
        """Return a mapping of object paths to public ids under a container."""
        return {}

    def get_object_meta(self, user, account, container, name, domain=None,
                        version=None, include_user_defined=True):
        """Return a dictionary with the object metadata for the domain.

        The keys returned are all user-defined, except:
            'name': The object name

            'bytes': The total data size

            'type': The content type

            'hash': The hashmap hash

            'modified': Last modification timestamp (overall)

            'modified_by': The user that committed the object
                           (version requested)

            'version': The version identifier

            'version_timestamp': The version's modification timestamp

            'uuid': A unique identifier that persists data or metadata updates
                    and renames

            'checksum': The MD5 sum of the object (may be empty)

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container/object does not exist

            VersionNotExists: Version does not exist

            ValueError: if domain is None and include_user_defined==True
        """
        return {}

    def update_object_meta(self, user, account, container, name, domain, meta,
                           replace=False):
        """Update object metadata for a domain and return the new version.

        Parameters:
            'domain': Metadata domain

            'meta': Dictionary with metadata to update

            'replace': Replace instead of update

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container/object does not exist

            LimitExceeded: if the metadata number exceeds the allowed limit.
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

    def update_object_permissions(self, user, account, container, name,
                                  permissions):
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

    def register_object_map(self, user, account, container, name, size, type,
                            mapfile, checksum='', domain='pithos', meta=None,
                            replace_meta=False, permissions=None):
        """Register an object mapfile without providing any data.

        Lock the container path, create a node pointing to the object path,
        create a version pointing to the mapfile
        and issue the size change in the quotaholder.

        :param user: the user account which performs the action

        :param account: the account under which the object resides

        :param container: the container under which the object resides

        :param name: the object name

        :param size: the object size

        :param type: the object mimetype

        :param mapfile: the mapfile pointing to the object data

        :param checkcum: the md5 checksum (optional)

        :param domain: the object domain

        :param meta: a dict with custom object metadata

        :param replace_meta: replace existing metadata or not

        :param permissions: a dict with the read and write object permissions

        :returns: the new object uuid

        :raises: ItemNotExists, NotAllowedError, QuotaError, LimitExceeded
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

    def update_object_hashmap(self, user, account, container, name, size, type,
                              hashmap, checksum, domain, meta=None,
                              replace_meta=False, permissions=None):
        """Create/update an object's hashmap and return the new version.

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

            LimitExceeded: if the metadata number exceeds the allowed limit.
        """
        return ''

    def update_object_checksum(self, user, account, container, name, version,
                               checksum):
        """Update an object's checksum."""
        return

    def copy_object(self, user, src_account, src_container, src_name,
                    dest_account, dest_container, dest_name, type, domain,
                    meta=None, replace_meta=False, permissions=None,
                    src_version=None, delimiter=None):
        """Copy an object's data and metadata and return the new version.

        Parameters:
            'domain': Metadata domain

            'meta': Dictionary with metadata to change from source
                    to destination

            'replace_meta': Replace metadata instead of update

            'permissions': New object permissions

            'src_version': Copy from the version provided

            'delimiter': Copy objects whose path starts with
                         src_name + delimiter

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container/object does not exist

            VersionNotExists: Version does not exist

            ValueError: Invalid users/groups in permissions

            QuotaError: Account or container quota exceeded

            LimitExceeded: if the metadata number exceeds the allowed limit.
        """
        return ''

    def move_object(self, user, src_account, src_container, src_name,
                    dest_account, dest_container, dest_name, type, domain,
                    meta=None, replace_meta=False, permissions=None,
                    delimiter=None):
        """Move an object's data and metadata and return the new version.

        Parameters:
            'domain': Metadata domain

            'meta': Dictionary with metadata to change from source
                    to destination

            'replace_meta': Replace metadata instead of update

            'permissions': New object permissions

            'delimiter': Move objects whose path starts with
                         src_name + delimiter

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container/object does not exist

            ValueError: Invalid users/groups in permissions

            QuotaError: Account or container quota exceeded
        """
        return ''

    def delete_object(self, user, account, container, name, until=None,
                      delimiter=None):
        """Delete/purge an object.

        Parameters:
            'delimiter': Delete objects whose path starting with
                         name + delimiter

        Raises:
            NotAllowedError: Operation not permitted

            ItemNotExists: Container/object does not exist
        """
        return

    def list_versions(self, user, account, container, name):
        """Return a list of all object (version, version_timestamp) tuples.

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

    def update_block(self, hash, data, offset=0, is_snapshot=False):
        """Update a known block and return the hash.

        Raises:
            IndexError: Offset or data outside block limits
        """
        return 0

    def get_domain_objects(self, domain, user=None):
        """Return a list of tuples for objects under the domain.

        Parameters:
            'user': return only objects accessible to the user.
        """
