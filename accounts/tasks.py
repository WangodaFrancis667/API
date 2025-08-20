from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.template.defaultfilters import date as date_filter
from django.template.loader import render_to_string

from .models import EmailVerification
from .utils.utils import mailer

import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 5})
def send_verification_email_task(self, verification_id: int):
    """Send email verification code - main implementation."""
    try:
        ver = EmailVerification.objects.select_related('user').get(id=verification_id)

        if ver.verified:
            logger.info("Verification %s already verified, skipping send.", verification_id)
            return True
        
        subject = getattr(settings, 'APP_NAME', 'AfroBuy Uganda') + " Email Verification Code"
        context = {
            'code': ver.verification_code,
            'user': ver.user,
            'email': ver.email,
            'expires_at': ver.expires_at,
            'expires_at_human': date_filter(ver.expires_at, "DATETIME_FORMAT"),
            'site_name': getattr(settings, 'SITE_NAME', getattr(settings, 'APP_NAME', 'AfroBuy')),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', settings.EMAIL_HOST_USER),
            'support_whatsapp': getattr(settings, 'SUPPORT_WHATSAPP', ''),
            'whatsapp_url': getattr(settings, 'WHATSAPP_URL', ''),
            'valid_minutes': 10
        }

        # Try using send_template first, fallback to send if not available
        try:
            ok = mailer.send_template(
                to=ver.email,
                subject=subject,
                template_name='emails/verification_email.html',
                context=context,
                bcc=getattr(settings, 'VERIFICATION_BCC', []),
            )
        except AttributeError:
            # Fallback to render_to_string + send method
            html_message = render_to_string('emails/email_verification.html', context)
            ok = mailer.send(
                to=ver.email,
                subject=subject,
                html=html_message,
            )
        
        if not ok:
            raise RuntimeError("SMTP send failed")
        
        logger.info(f"Verification email sent successfully to: {ver.email}")
        return True
        
    except Exception as e:
        logger.error(f"Verification email task failed: {str(e)}")
        raise

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def send_password_reset_email_task(self, reset_id):
    """Send password reset email with verification code."""
    try:
        from .models import PasswordReset
        
        reset = PasswordReset.objects.select_related('user').get(id=reset_id)
        
        subject = f"{getattr(settings, 'SITE_NAME', 'afrobuyug')} - Password Reset Code"
        context = {
            'code': reset.verification_code,
            'user': reset.user,
            'expires_at': reset.expires_at,
            'site_name': getattr(settings, 'SITE_NAME', 'afrobuyug'),
            'valid_minutes': 15,
            'support_email': getattr(settings, 'SUPPORT_EMAIL', settings.EMAIL_HOST_USER),
        }
        
        # Try using send_template first, fallback to send if not available
        try:
            result = mailer.send_template(
                to=reset.email,
                subject=subject,
                template_name='emails/password_reset_email.html',
                context=context,
                bcc=getattr(settings, 'PASSWORD_RESET_BCC', []),
            )
        except AttributeError:
            # Fallback to render_to_string + send method
            html_message = render_to_string('emails/password_reset_email.html', context)
            result = mailer.send(
                to=reset.email,
                subject=subject,
                html=html_message,
            )
        
        if result:
            logger.info(f"Password reset email sent to: {reset.email}")
            return True
        else:
            logger.error(f"Failed to send password reset email to: {reset.email}")
            raise RuntimeError("SMTP send failed")
            
    except Exception as e:
        logger.error(f"Password reset email task failed: {str(e)}")
        raise

@shared_task(bind=True, max_retries=3)
def send_email_task(self, to, subject, template_name, context, bcc=None, copy_admin=False):
    """Generic email sending task."""
    try:
        return mailer.send_template(
            to=to,
            subject=subject,
            template_name=template_name,
            context=context,
            bcc=bcc,
            copy_admin=copy_admin,
        )
    except Exception as e:
        raise self.retry(exc=e, countdown=30)  # retry after 30s