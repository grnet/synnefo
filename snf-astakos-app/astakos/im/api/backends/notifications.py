def _send_admin_notification(template_name,
                             dictionary=None,
                             subject='alpha2 testing notification',):
    """
    Send notification email to settings.ADMINS.

    Raises SendNotificationError
    """
    if not settings.ADMINS:
        return
    dictionary = dictionary or {}
    message = render_to_string(template_name, dictionary)
    sender = settings.SERVER_EMAIL
    try:
        send_mail(subject,
                  message, sender, [i[1] for i in settings.ADMINS])
    except (SMTPException, socket.error) as e:
        logger.exception(e)
        raise SendNotificationError()
    else:
        msg = 'Sent admin notification for user %s' % dictionary
        logger.log(LOGGING_LEVEL, msg)

class EmailNotification(Notification):
    def send(self):
        send_mail(
            subject,
            message,
            sender,
            recipients
        )
    )

class Notification(object):
    def __init__(self, sender, recipients, subject, message):
        self.sender = sender
        self.recipients = recipients
        self.subject = subject
        self.message = message
    
    def send(self):
        pass