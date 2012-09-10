from pithos.api.settings import (BACKEND_DB_MODULE, BACKEND_DB_CONNECTION,
                                 BACKEND_BLOCK_MODULE, BACKEND_BLOCK_PATH,
                                 BACKEND_BLOCK_UMASK,
                                 BACKEND_QUEUE_MODULE, BACKEND_QUEUE_CONNECTION,
                                 BACKEND_QUOTA, BACKEND_VERSIONING)
from pithos.backends import connect_backend
from pithos.api.util import hashmap_md5

from django.core.mail import send_mail
from django.utils.translation import ugettext as _

from astakos.im.settings import DEFAULT_FROM_EMAIL

import socket
from smtplib import SMTPException


def update_md5(m):
    if m['resource'] != 'object' or m['details']['action'] != 'object update':
        return

    backend = connect_backend(db_module=BACKEND_DB_MODULE,
                              db_connection=BACKEND_DB_CONNECTION,
                              block_module=BACKEND_BLOCK_MODULE,
                              block_path=BACKEND_BLOCK_PATH,
                              block_umask=BACKEND_BLOCK_UMASK,
                              queue_module=BACKEND_QUEUE_MODULE,
                              queue_connection=BACKEND_QUEUE_CONNECTION)
    backend.default_policy['quota'] = BACKEND_QUOTA
    backend.default_policy['versioning'] = BACKEND_VERSIONING

    path = m['value']
    account, container, name = path.split('/', 2)
    version = m['details']['version']
    meta = None
    try:
        meta = backend.get_object_meta(
            account, account, container, name, 'pithos', version)
        if meta['checksum'] == '':
            size, hashmap = backend.get_object_hashmap(
                account, account, container, name, version)
            checksum = hashmap_md5(backend, hashmap, size)
            backend.update_object_checksum(
                account, account, container, name, version, checksum)
            print 'INFO: Updated checksum for path "%s"' % (path,)
    except Exception, e:
        print 'WARNING: Can not update checksum for path "%s" (%s)' % (path, e)

    backend.close()


def send_sharing_notification(m):
    if m['resource'] != 'sharing':
        return

    members = m['details']['members']
    user = m['details']['user']
    path = m['value']
    account, container, name = path.split('/', 2)

    subject = 'Invitation to a Pithos+ shared object'
    from_email = DEFAULT_FROM_EMAIL
    recipient_list = members
    message = 'User %s has invited you to a Pithos+ shared object. You can view it under "Shared to me" at "%s".' % (user, path)
    try:
        send_mail(subject, message, from_email, recipient_list)
        print 'INFO: Sharing notification sent for path "%s" to %s' % (
            path, ','.join(recipient_list))
    except (SMTPException, socket.error) as e:
        print 'WARNING: Can not update send email for sharing "%s" (%s)' % (
            path, e)
