# Copyright 2011 GRNET S.A. All rights reserved.
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

class NotAllowedError(Exception):
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
    """
    
    def list_accounts(self, user, marker=None, limit=10000):
        """Return a list of accounts the user can access.
        
        Parameters:
            'marker': Start list from the next item after 'marker'
            'limit': Number of containers to return
        """
        return []
    
    def get_account_meta(self, user, account, until=None):
        """Return a dictionary with the account metadata.
        
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
    
    def update_account_meta(self, user, account, meta, replace=False):
        """Update the metadata associated with the account.
        
        Parameters:
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
    
    def put_account(self, user, account):
        """Create a new account with the given name.
        
        Raises:
            NotAllowedError: Operation not permitted
        """
        return
    
    def delete_account(self, user, account):
        """Delete the account with the given name.
        
        Raises:
            NotAllowedError: Operation not permitted
            IndexError: Account is not empty
        """
        return
    
    def list_containers(self, user, account, marker=None, limit=10000, shared=False, until=None):
        """Return a list of container names existing under an account.
        
        Parameters:
            'marker': Start list from the next item after 'marker'
            'limit': Number of containers to return
            'shared': Only list containers with permissions set
        
        Raises:
            NotAllowedError: Operation not permitted
        """
        return []
    
    def get_container_meta(self, user, account, container, until=None):
        """Return a dictionary with the container metadata.
        
        The keys returned are all user-defined, except:
            'name': The container name
            'count': The number of objects
            'bytes': The total data size
            'modified': Last modification timestamp (overall)
            'until_timestamp': Last modification until the timestamp provided
        
        Raises:
            NotAllowedError: Operation not permitted
            NameError: Container does not exist
        """
        return {}
    
    def update_container_meta(self, user, account, container, meta, replace=False):
        """Update the metadata associated with the container.
        
        Parameters:
            'meta': Dictionary with metadata to update
            'replace': Replace instead of update
        
        Raises:
            NotAllowedError: Operation not permitted
            NameError: Container does not exist
        """
        return
    
    def get_container_policy(self, user, account, container):
        """Return a dictionary with the container policy.
        
        The keys returned are:
            'quota': The maximum bytes allowed (default is 0 - unlimited)
            'versioning': Can be 'auto', 'manual' or 'none' (default is 'manual')
        
        Raises:
            NotAllowedError: Operation not permitted
            NameError: Container does not exist
        """
        return {}
    
    def update_container_policy(self, user, account, container, policy, replace=False):
        """Update the policy associated with the account.
        
        Raises:
            NotAllowedError: Operation not permitted
            NameError: Container does not exist
            ValueError: Invalid policy defined
        """
        return
    
    def put_container(self, user, account, container, policy=None):
        """Create a new container with the given name.
        
        Raises:
            NotAllowedError: Operation not permitted
            NameError: Container already exists
            ValueError: Invalid policy defined
        """
        return
    
    def delete_container(self, user, account, container, until=None):
        """Delete/purge the container with the given name.
        
        Raises:
            NotAllowedError: Operation not permitted
            NameError: Container does not exist
            IndexError: Container is not empty
        """
        return
    
    def list_objects(self, user, account, container, prefix='', delimiter=None, marker=None, limit=10000, virtual=True, keys=[], shared=False, until=None):
        """Return a list of object (name, version_id) tuples existing under a container.
        
        Parameters:
            'prefix': List objects starting with 'prefix'
            'delimiter': Return unique names before 'delimiter' and after 'prefix'
            'marker': Start list from the next item after 'marker'
            'limit': Number of objects to return
            'virtual': If not set, the result will only include names starting\
                       with 'prefix' and ending without a 'delimiter' or with\
                       the first occurance of the 'delimiter' after 'prefix'.\
                       If set, the result will include all names after 'prefix',\
                       up to and including the 'delimiter' if it is found
            'keys': Include objects that have meta with the keys in the list
            'shared': Only list objects with permissions set
        
        Raises:
            NotAllowedError: Operation not permitted
            NameError: Container does not exist
        """
        return []
    
    def list_object_meta(self, user, account, container, until=None):
        """Return a list with all the container's object meta keys.
        
        Raises:
            NotAllowedError: Operation not permitted
            NameError: Container does not exist
        """
        return []
    
    def get_object_meta(self, user, account, container, name, version=None):
        """Return a dictionary with the object metadata.
        
        The keys returned are all user-defined, except:
            'name': The object name
            'bytes': The total data size
            'modified': Last modification timestamp (overall)
            'modified_by': The user that committed the object (version requested)
            'version': The version identifier
            'version_timestamp': The version's modification timestamp
        
        Raises:
            NotAllowedError: Operation not permitted
            NameError: Container/object does not exist
            IndexError: Version does not exist
        """
        return {}
    
    def update_object_meta(self, user, account, container, name, meta, replace=False):
        """Update the metadata associated with the object.
        
        Parameters:
            'meta': Dictionary with metadata to update
            'replace': Replace instead of update
        
        Raises:
            NotAllowedError: Operation not permitted
            NameError: Container/object does not exist
        """
        return
    
    def get_object_permissions(self, user, account, container, name):
        """Return the path from which this object gets its permissions from,\
        along with a dictionary containing the permissions.
        
        The keys are:
            'read': The object is readable by the users/groups in the list
            'write': The object is writable by the users/groups in the list
        
        Raises:
            NotAllowedError: Operation not permitted
            NameError: Container/object does not exist
        """
        return {}
    
    def update_object_permissions(self, user, account, container, name, permissions):
        """Update the permissions associated with the object.
        
        Parameters:
            'permissions': Dictionary with permissions to update
        
        Raises:
            NotAllowedError: Operation not permitted
            NameError: Container/object does not exist
            ValueError: Invalid users/groups in permissions
            AttributeError: Can not set permissions, as this object\
                is already shared/private by another object higher\
                in the hierarchy, or setting permissions here will\
                invalidate other permissions deeper in the hierarchy
        """
        return
    
    def get_object_public(self, user, account, container, name):
        """Return the public URL of the object if applicable.
        
        Raises:
            NotAllowedError: Operation not permitted
            NameError: Container/object does not exist
        """
        return None
    
    def update_object_public(self, user, account, container, name, public):
        """Update the public status of the object.
        
        Parameters:
            'public': Boolean value
        
        Raises:
            NotAllowedError: Operation not permitted
            NameError: Container/object does not exist
        """
        return
    
    def get_object_hashmap(self, user, account, container, name, version=None):
        """Return the object's size and a list with partial hashes.
        
        Raises:
            NotAllowedError: Operation not permitted
            NameError: Container/object does not exist
            IndexError: Version does not exist
        """
        return 0, []
    
    def update_object_hashmap(self, user, account, container, name, size, hashmap, meta={}, replace_meta=False, permissions=None):
        """Create/update an object with the specified size and partial hashes.
        
        Parameters:
            'dest_meta': Dictionary with metadata to change
            'replace_meta': Replace metadata instead of update
            'permissions': Updated object permissions
        
        Raises:
            NotAllowedError: Operation not permitted
            NameError: Container does not exist
            ValueError: Invalid users/groups in permissions
            AttributeError: Can not set permissions
        """
        return
    
    def copy_object(self, user, account, src_container, src_name, dest_container, dest_name, dest_meta={}, replace_meta=False, permissions=None, src_version=None):
        """Copy an object's data and metadata.
        
        Parameters:
            'dest_meta': Dictionary with metadata to change from source to destination
            'replace_meta': Replace metadata instead of update
            'permissions': New object permissions
            'src_version': Copy from the version provided
        
        Raises:
            NotAllowedError: Operation not permitted
            NameError: Container/object does not exist
            IndexError: Version does not exist
            ValueError: Invalid users/groups in permissions
            AttributeError: Can not set permissions
        """
        return
    
    def move_object(self, user, account, src_container, src_name, dest_container, dest_name, dest_meta={}, replace_meta=False, permissions=None):
        """Move an object's data and metadata.
        
        Parameters:
            'dest_meta': Dictionary with metadata to change from source to destination
            'replace_meta': Replace metadata instead of update
            'permissions': New object permissions
        
        Raises:
            NotAllowedError: Operation not permitted
            NameError: Container/object does not exist
            ValueError: Invalid users/groups in permissions
            AttributeError: Can not set permissions
        """
        return
    
    def delete_object(self, user, account, container, name, until=None):
        """Delete/purge an object.
        
        Raises:
            NotAllowedError: Operation not permitted
            NameError: Container/object does not exist
        """
        return
    
    def list_versions(self, user, account, container, name):
        """Return a list of all (version, version_timestamp) tuples for an object.
        
        Raises:
            NotAllowedError: Operation not permitted
        """
        return []
    
    def get_block(self, hash):
        """Return a block's data.
        
        Raises:
            NameError: Block does not exist
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
