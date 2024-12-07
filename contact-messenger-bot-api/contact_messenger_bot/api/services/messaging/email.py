import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from contact_messenger_bot.api.settings import settings

logger = logging.getLogger(__name__)


def send_message(sender: str, recipient: str, body: str, subject: str) -> None:
    if settings.email is None:
        return  # not supported

    sender_email = sender
    receiver_email = recipient

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(settings.email.host, settings.email.port) as s:
        if settings.email.auth:
            logger.debug("Authenticating as %s", settings.email.auth.user)
            s.starttls()
            s.login(settings.email.auth.user, settings.email.auth.password)

        logger.info("Sending email:\n%s", msg)
        s.send_message(msg)
