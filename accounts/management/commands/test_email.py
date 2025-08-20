from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.conf import settings
from accounts.utils.utils import mailer

class Command(BaseCommand):
    help = 'Test email configuration'

    def add_arguments(self, parser):
        parser.add_argument('--to', type=str, help='Email address to send to')

    def handle(self, *args, **options):
        to_email = options.get('to', 'fwangoda@gmail.com')
        
        # Test basic email
        try:
            result = mailer.send(
                to=to_email,
                subject="Test Email from Django",
                html="<h1>Test Email</h1><p>This is a test email from your Django app.</p>"
            )
            
            if result:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully sent test email to {to_email}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Failed to send test email to {to_email}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Email test failed: {str(e)}')
            )