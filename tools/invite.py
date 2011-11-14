#!/usr/bin/env python

import sys

if len(sys.argv) != 4:
	print "Usage: %s <inviter token> <invitee name> <invitee email>" % (sys.argv[0],)
	sys.exit(-1)

import httplib2
http = httplib2.Http(disable_ssl_certificate_validation=True)

url = 'https://pithos.dev.grnet.gr/im/invite'

import urllib
params = urllib.urlencode({
	'uniq': sys.argv[3],
	'realname': sys.argv[2]
})

response, content = http.request(url, 'POST', params,
	headers={'Content-type': 'application/x-www-form-urlencoded', 'X-Auth-Token': sys.argv[1]}
)

if response['status'] == '200':
	print 'OK'
	sys.exit(0)
else:
	print response, content
	sys.exit(-1)
