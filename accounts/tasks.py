from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.template.defaultfilters import date as date_filter

from .models import EmailVerification
from .utils.utils import mailer

import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 5})
def send_verification_email_task(self, verification_id: int):
    ver = EmailVerification.objects.select_related('user').get(id=verification_id)

    if ver.verified:
        logger.info("Verification %s already verified, skipping send.", verification_id)
        return
    
    subject = getattr(settings, 'APP_NAME', 'Our App') + " — Email Verification Code"
    context = {
        'code': ver.verification_code,
        'user': ver.user,
        'email': ver.email,
        'expires_at': ver.expires_at,
        'expires_at_human': date_filter(ver.expires_at, "DATETIME_FORMAT"),
        'site_name': getattr(settings, 'SITE_NAME', getattr(settings, 'APP_NAME', 'AfroBuy')),
        'support_email': getattr(settings, 'SUPPORT_EMAIL', settings.EMAIL_HOST_USER),
    }

    ok = mailer.send_template(
        to=ver.email,
        subject=subject,
        template_name='emails/verification_email.html',
        context=context,
        bcc=getattr(settings, 'VERIFICATION_BCC', []),
    )
    if not ok:
        raise RuntimeError("SMTP send failed")