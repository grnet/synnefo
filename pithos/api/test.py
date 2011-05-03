import cloudfiles

conn = cloudfiles.get_connection('jsmith', '1234567890', authurl = 'http://127.0.0.1:8000/v1')
print 'Authenticated. Token: %s' % conn.token
print 'Container count: %d Total bytes: %d' % conn.get_info()

container = 'asdf'
conn.create_container(container)

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

objects = cont.list_objects()
print 'Found: %d objects' % len(objects)
for object in objects:
    print object
    cont.delete_object(object)

object = 'test_file'
obj = cont.create_object(object)
obj.content_type = 'text/plain'
obj.metadata['blah'] = 'aldsjflkajdsflk'
obj.write('asdfasdfasdf')
obj.metadata
print ''
print 'OBJECT'
print 'Name: %s' % obj.name
print 'Content Type: %s' % obj.content_type
print 'Size: %s' % obj.size
print 'Last Modified: %s' % obj.last_modified
print 'Container: %s' % obj.container
print 'Metadata: %s' % obj.metadata

obj = cont.get_object(object)
data = obj.read()
print ''
print 'OBJECT'
print 'Name: %s' % obj.name
print 'Content Type: %s' % obj.content_type
print 'Size: %s' % obj.size
print 'Last Modified: %s' % obj.last_modified
print 'Container: %s' % obj.container
print 'Metadata: %s' % obj.metadata

print 'Data: %s' % data

cont.delete_object(object)
conn.delete_container(container)
