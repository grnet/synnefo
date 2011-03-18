DEFAULT_HOST = '127.0.0.1:8000'
DEFAULT_API = 'v1.1redux'


def address_to_string(address):
    key = address['id']
    val = ' '.join(ip['addr'] for ip in address['values'])
    return '%s: %s' % (key, val)

def print_server(server):
    for key, val in sorted(server.items()):
        if key == 'metadata':
            val = ', '.join('%s="%s"' % x for x in val['values'].items())
        if key == 'addresses':
            val = ', '.join(address_to_string(address) for address in val['values'])
        print '%s: %s' % (key.rjust(12), val)
