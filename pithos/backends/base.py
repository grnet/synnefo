class BaseBackend(object):
    """Abstract backend class that serves as a reference for actual implementations
    
    The purpose of the backend is to provide the necessary functions for handling data
    and metadata. It is responsible for the actual storage and retrieval of information.
    
    Note that the account level is always valid as it is checked from another subsystem.
    """
    
    def get_account_meta(self, account):
        """Return a dictionary with the account metadata
        
        The keys returned are all user-defined, except:
            'name': The account name
            'count': The number of containers (or 0)
            'bytes': The total data size (or 0)
            'modified': Last modification timestamp
        """
        return {}
    
    def update_account_meta(self, account, meta):
        """Update the metadata associated with the account
        
        Parameters:
            'meta': Dictionary with metadata to update
        """
        return
    
    def create_container(self, account, name):
        """Create a new container with the given name

        Raises:
            NameError: Container already exists
        """
        return
    
    def delete_container(self, account, name):
        """Delete the container with the given name

        Raises:
            NameError: Container does not exist
            IndexError: Container is not empty
        """
        return
    
    def get_container_meta(self, account, name):
        """Return a dictionary with the container metadata

        The keys returned are all user-defined, except:
            'name': The container name
            'count': The number of objects
            'bytes': The total data size
            'modified': Last modification timestamp
        
        Raises:
            NameError: Container does not exist
        """
        return {}
    
    def update_container_meta(self, account, name, meta):
        """Update the metadata associated with the container
        
        Parameters:
            'meta': Dictionary with metadata to update
        
        Raises:
            NameError: Container does not exist
        """
        return
    
    def list_containers(self, account, marker=None, limit=10000):
        """Return a list of containers existing under an account
        
        Parameters:
            'marker': Start list from the next item after 'marker'
            'limit': Number of containers to return
        """
        return []
    
    def list_objects(self, account, container, prefix='', delimiter=None, marker=None, limit=10000, virtual=True):
        """Return a list of objects existing under a container
        
        Parameters:
            'prefix': List objects starting with 'prefix'
            'delimiter': Return unique names before 'delimiter' and after 'prefix'
            'marker': Start list from the next item after 'marker'
            'limit': Number of objects to return
            'virtual': If not set, the result will only include names starting
                with 'prefix' and ending without a 'delimiter' or with the first
                occurance of the 'delimiter' after 'prefix'.
                If set, the result will include all names after 'prefix', up to and
                including the 'delimiter' if it is found
        
        Raises:
            NameError: Container does not exist
        """
        return []
    
    def get_object_meta(self, account, container, name):
        """Return a dictionary with the object metadata
        
        The keys returned are all user-defined, except:
            'name': The account name
            'bytes': The total data size
            'modified': Last modification timestamp
        
        Raises:
            NameError: Container/object does not exist
        """
        return {}
    
    def update_object_meta(self, account, container, name, meta):
        """Update the metadata associated with the object
        
        Parameters:
            'meta': Dictionary with metadata to update
        
        Raises:
            NameError: Container/object does not exist
        """
        return
    
    def get_object(self, account, container, name, offset=0, length=-1):
        """Return the object data
        
        Parameters:
            'offset': Offset in the object to start reading from
            'length': Number of bytes to return
        
        Raises:
            NameError: Container/object does not exist
        """
        return ''
    
    def update_object(self, account, container, name, data, offset=0):
        """Create/update an object with the specified data
        
        Parameters:
            'offset': Offset in the object to start writing from
        
        Raises:
            NameError: Container does not exist
        """
        return
    
    def copy_object(self, account, src_container, src_name, dest_container, dest_name, dest_meta={}):
        """Copy an object's data and metadata
        
        Parameters:
            'dest_meta': Dictionary with metadata to changes from source to destination
        
        Raises:
            NameError: Container/object does not exist
        """
        return
    
    def move_object(self, account, src_container, src_name, dest_container, dest_name, dest_meta={}):
        """Move an object's data and metadata
        
        Parameters:
            'dest_meta': Dictionary with metadata to changes from source to destination
        
        Raises:
            NameError: Container/object does not exist
        """
        return
    
    def delete_object(self, account, container, name):
        """Delete an object
        
        Raises:
            NameError: Container/object does not exist
        """
        return
