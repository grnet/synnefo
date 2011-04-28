import cloudfiles

conn = cloudfiles.get_connection('jsmith', '1234567890', authurl = 'http://127.0.0.1:8000/v1')
print 'Authenticated. Token: %s' % conn.token
print 'Container count: %d Total bytes: %d' % conn.get_info()

containers = conn.get_all_containers()
print 'Found: %d containers' % len(containers)
for container in containers:
    print container.name

containers = conn.list_containers_info()
for container in containers:
    print container

container = 'asdf'
conn.create_container(container)

cont = conn.get_container(container)
print 'Got container %s.' % container
print 'Object count: %s Total bytes: %s' % (cont.object_count, cont.size_used)

conn.delete_container(container)
