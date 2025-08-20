import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class Mail:
    def __init__(
        self,
        host,
        port,
        user,
        password,
        use_tls=True,
        use_ssl=False,
        default_from=None,
        admin_copy=None,  # optional email for copies
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.default_from = default_from or user
        self.admin_copy = admin_copy


    def _connect(self):
        """Establish an SMTP connection."""
        try:
            if self.use_ssl or self.port == 465:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=30)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=30)
                if self.use_tls:
                    server.starttls()
            server.login(self.user, self.password)
            return server
        except Exception as e:
            logger.error("SMTP connection failed: %s", str(e), exc_info=True)
            raise

    def send_html(self, *, to, subject, html, text_alt=None, bcc=None, copy_admin=False):
        """
        Send an HTML email (with plain-text fallback).
        """
        try:
            app_name = getattr(settings, "APP_NAME", "AfroBuy")
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{app_name} <{self.default_from}>"
            msg["To"] = to
            msg["Subject"] = subject

            if not text_alt:
                text_alt = strip_tags(html)

            msg.attach(MIMEText(text_alt, "plain"))
            msg.attach(MIMEText(html, "html"))

            recipients = [to]

            if bcc:
                recipients.extend(bcc)

            if copy_admin and self.admin_copy:
                recipients.append(self.admin_copy)

            server = self._connect()
            server.sendmail(self.default_from, recipients, msg.as_string())
            server.quit()

            logger.info("Email successfully sent to %s", recipients)
            return True

        except Exception as e:
            logger.error("SMTP_MAIL_ERROR: %s", str(e), exc_info=True)
            return False

    def send_template(self, *, to, subject, template_name, context, bcc=None, copy_admin=False):
        """
        Send email rendered from a Django template.
        """
        try:
            html = render_to_string(template_name, context)
            return self.send_html(
                to=to,
                subject=subject,
                html=html,
                bcc=bcc,
                copy_admin=copy_admin,
            )
        except Exception as e:
            logger.error("TEMPLATE_RENDER_ERROR: %s", str(e), exc_info=True)
            return False


# Shared mailer instance
mailer = Mail(
    host=settings.EMAIL_HOST,
    port=settings.EMAIL_PORT,
    user=settings.EMAIL_HOST_USER,
    password=settings.EMAIL_HOST_PASSWORD,
    use_tls=getattr(settings, "EMAIL_USE_TLS", True),
    use_ssl=getattr(settings, "EMAIL_USE_SSL", False),
    default_from=getattr(settings, "DEFAULT_FROM_EMAIL", None),
    admin_copy=getattr(settings, "ADMIN_EMAIL", None),  # optional
)
