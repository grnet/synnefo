class BaseBackEnd:
    def get_account_meta(self, account):
        """
        returns a dictionary with the account metadata
        """
        return {}

    def update_account_meta(self, account, meta):
        """
        updates the metadata associated with the account
        """
        return
    
    def create_container(self, account, name):
        """
        creates a new container with the given name
        if it doesn't exist under the basepath
        """
        return
    
    def delete_container(self, account, name):
        """
        deletes the container with the given name
        if it exists under the basepath and is empty
        """
        return
    
    def get_container_meta(self, account, name):
        """
        returns a dictionary with the container metadata
        """
        return {}
    
    def update_container_meta(self, account, name, meta):
        """
        updates the metadata associated with the container
        """
        return
    
    def list_containers(self, account, marker = None, limit = 10000):
        """
        returns a list of at most limit (default = 10000) containers 
        starting from the next item after the optional marker
        """
        return []
    
    def list_objects(self, account, container, prefix = '', delimiter = None, marker = None, limit = 10000):
        """
        returns a list of objects existing under a container
        """
        return []
    
    def get_object_meta(self, account, container, name, keys = None):
        """
        returns a dictionary with the object metadata
        """
        return {}
    
    def update_object_meta(self, account, container, name, meta):
        """
        updates the metadata associated with the object
        """
        return
    
    def get_object(self, account, container, name, offset = 0, length = -1):
        """
        returns the object data
        """
        return

    def update_object(self, account, container, name, data, offset = 0):
        """
        creates/updates an object with the specified data
        """
        return
    
    def copy_object(self, account, src_container, src_name, dest_container, dest_name):
        """
        copies an object
        """
        return
    
    def delete_object(self, account, container, name):
        """
        deletes an object
        """
        return


