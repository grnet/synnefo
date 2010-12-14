#from libcloud.types import Provider 
#from libcloud.providers import get_driver 

#USERNAME = 'user'
#SECRET = 'secret'

def home(request):
    return {'project':'+nefo'}

def instances(request):
    #Driver = get_driver(Provider.RACKSPACE) 
    #conn = Driver(USER, SECRET) 
    #nodes = conn.list_nodes()
    nodes = []
    nodes.append({'id':1, 'name':'My mail server', 'state':'3','public_ip':'147.102.1.62',})
    nodes.append({'id':2, 'name':'My name server', 'state':'3','public_ip':'147.102.1.64',})
    return {'nodes': nodes, 'images': images(request)['images']}

def storage(request):
    return {}

def images(request):
    #Driver = get_driver(Provider.RACKSPACE) 
    #conn = Driver(USER, SECRET) 
    #nodes = conn.list_images()     
    images = [
              {'id': 'ubuntu-10.10-x86_64-server', 'type':'standard', 'title': 'Ubuntu 10.10 server 64bit', 'description': 'Apache, MySQL, php5 preinstalled', 'size': '834', 'logo':'/static/ubuntu.png'}, 
              {'id': 'fedora-14-desktop', 'type':'standard', 'title': 'Fedora 14 desktop 32bit', 'description': 'Apache, MySQL, php5 preinstalled', 'size': '912', 'logo':'/static/fedora.png'}, 
              {'id': 'windows7-pro', 'type':'standard', 'title': 'Windows 7 professional', 'description': 'MS Office 7 preinstalled', 'size': '8142', 'logo':'/static/windows.png'}, 
              {'id': 'windows-xp', 'type':'custom', 'title': 'Windows XP', 'description': 'MS Office XP preinstalled', 'size': '6192', 'logo':'/static/windows.png'}, 
             ]
    return {'images': images}

def network(request):
    return {}
