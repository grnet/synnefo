def home(request):
    return {'project':'+nefo'}

def instances(request):
    nodes = []
    nodes.append({'id':1, 'name':'My mail server', 'state':'3','public_ip':'147.102.1.62', 'thumb' : 'ubuntu.png'})
    nodes.append({'id':2, 'name':'My name server', 'state':'3','public_ip':'147.102.1.64', 'thumb' : 'debian.png'})
    nodes.append({'id':3, 'name':'My file server', 'state':'3','public_ip':'147.102.1.65', 'thumb' : 'fedora.png'})
    nodes.append({'id':4, 'name':'My torrent server', 'state':'3','public_ip':'147.102.1.66', 'thumb' : 'gentoo.png'})
    nodes.append({'id':5, 'name':'My firewall', 'state':'3','public_ip':'147.102.1.67', 'thumb' : 'netbsd.png'})
    nodes.append({'id':6, 'name':'My windows workstation', 'state':'0','public_ip':'147.102.1.69', 'thumb' : 'windows.png'})
    return {'nodes': nodes, 'images': images(request)['images']}

def storage(request):
    return {}

def images(request): 
    images = [
              {'id': 'ubuntu-10.10-x86_64-server', 'type':'standard', 'title': 'Ubuntu 10.10 server 64bit', 'description': 'Apache, MySQL, php5 preinstalled', 'size': '834', 'logo':'/static/ubuntu.png'}, 
              {'id': 'fedora-14-desktop', 'type':'standard', 'title': 'Fedora 14 desktop 32bit', 'description': 'Apache, MySQL, php5 preinstalled', 'size': '912', 'logo':'/static/fedora.png'}, 
              {'id': 'windows7-pro', 'type':'standard', 'title': 'Windows 7 professional', 'description': 'MS Office 7 preinstalled', 'size': '8142', 'logo':'/static/windows.png'}, 
              {'id': 'windows-xp', 'type':'standard', 'title': 'Windows XP', 'description': 'MS Office XP preinstalled', 'size': '6192', 'logo':'/static/windows.png'},
              {'id': 'netbsd-server', 'type':'custom', 'title': 'NetBSD server', 'description': 'my secure torrent server', 'size': '898', 'logo':'/static/netbsd.png'}, 
              {'id': 'gentoo-playroom', 'type':'custom', 'title': 'Centoo', 'description': 'online pinaball olympiad server', 'size': '912', 'logo':'/static/gentoo.png'},  
             ]
    return {'images': images}

def network(request):
    return {}
