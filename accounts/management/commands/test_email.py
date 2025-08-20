from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.conf import settings

class Command(BaseCommand):
    help = 'Test email configuration'

    def add_arguments(self, parser):
        parser.add_argument('--to', type=str, help='Email address to send to')

    def handle(self, *args, **options):
        to_email = options.get('to', 'fwangoda@gmail.com')
        
        # First, let's see what mailer actually is
        try:
            from accounts.utils.utils import mailer
            self.stdout.write(f"Mailer type: {type(mailer)}")
            self.stdout.write(f"Mailer attributes: {dir(mailer)}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Import error: {str(e)}'))
            return
        
        # Test with Django's built-in email first
        try:
            from django.core.mail import send_mail
            
            result = send_mail(
                subject="Test Email from Django",
                message="This is a test email from your Django app.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                html_message="<h1>Test Email</h1><p>This is a test email from your Django app.</p>",
                fail_silently=False,
            )
            
            if result:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully sent test email to {to_email} using Django send_mail')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Failed to send test email to {to_email}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Django send_mail failed: {str(e)}')
            )
        
        # Now test with your custom mailer if it has the right methods
        try:
            if hasattr(mailer, 'send'):
                result = mailer.send(
                    to=to_email,
                    subject="Test Email with Custom Mailer",
                    html="<h1>Test Email</h1><p>This is a test email from your custom mailer.</p>"
                )
                
                if result:
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully sent test email to {to_email} using custom mailer')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to send test email with custom mailer to {to_email}')
                    )
            else:
                self.stdout.write(
                    self.style.WARNING('Custom mailer does not have send method')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Custom mailer test failed: {str(e)}')
            )