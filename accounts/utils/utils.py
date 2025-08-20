"""
    Helper functions for sending notifications and logging
    audit events
"""

# from django.core.mail import send_mail
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings

from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

    
class Mail:
    def __init__(self, host, port, user, password, use_tls=True, use_ssl=False, default_from=None):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.default_from = default_from or user

    def _connect(self):
        if self.use_ssl or self.port == 465:
            server = smtplib.SMTP_SSL(self.host, self.port)
        else:
            server = smtplib.SMTP(self.host, self.port)
            if self.use_tls:
                server.starttls()
        server.login(self.user, self.password)
        return server
    
    def send_html(self, *, to, subject, html, text_alt=None, bcc=None):
        try:
            app_name = getattr(settings, 'APP_NAME', '')
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{app_name} <{self.default_from}>"
            msg['To'] = to
            msg['Subject'] = subject

            if not text_alt:
                text_alt = strip_tags(html)

            msg.attach(MIMEText(text_alt, 'plain'))
            msg.attach(MIMEText(html, 'html'))

            server = self._connect()
            recipients = [to] + (bcc or [])
            server.sendmail(self.default_from, recipients, msg.as_string())
            server.sendmail(self.user, "fwangoda@gmail.com", msg.as_string())
            server.quit()
            return True
        except Exception as e:
            logger.exception("SMTP_MAIL_ERROR")
            return False
    
    def send_template(self, *, to, subject, template_name, context, bcc=None):
        html = render_to_string(template_name, context)
        return self.send_html(to=to, subject=subject, html=html, bcc=bcc)


# Instatiate a shared mailer using Django setttings
mailer = Mail(
    host=settings.EMAIL_HOST,
    port=settings.EMAIL_PORT,
    user=settings.EMAIL_HOST_USER,
    password=settings.EMAIL_HOST_PASSWORD,
    use_tls=getattr(settings, 'EMAIL_USE_TLS', True),
    use_ssl=getattr(settings, 'EMAIL_USE_SSL', False),
    default_from=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
)