#from libcloud.types import Provider 
#from libcloud.providers import get_driver 

#USERNAME = 'user'
#SECRET = 'secret'

def home(request):
    return {'project':'synnefo'}

def instances(request):
    #Driver = get_driver(Provider.RACKSPACE) 
    #conn = Driver(USER, SECRET) 
    #nodes = conn.list_nodes()     
    nodes = []
    nodes.append({'id':1, 'name':'My mail server', 'state':'3','public_ip':'147.102.1.62',})
    return {'nodes': nodes}

def storage(request):
    return {}

def images(request):
    #Driver = get_driver(Provider.RACKSPACE) 
    #conn = Driver(USER, SECRET) 
    #nodes = conn.list_images()     
    images = []
    return {'images': images}

def network(request):
    return {}
