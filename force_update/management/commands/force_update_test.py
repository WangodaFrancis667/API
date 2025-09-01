from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import reverse

class Command(BaseCommand):
    help = "Quickly test the force-update endpoint scenarios"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Test force update scenario")
        parser.add_argument("--optional", action="store_true", help="Test optional update scenario")
        parser.add_argument("--none", action="store_true", help="Test no update scenario")
        parser.add_argument("--build", type=int, default=0, help="Custom build number")
        parser.add_argument("--version", type=str, default="", help="Custom version string")

    def handle(self, *args, **options):
        client = Client()
        params = {}
        if options["force"]:
            params["test_force_update"] = "true"
        if options["optional"]:
            params["test_optional_update"] = "true"
        if options["none"]:
            params["test_no_update"] = "true"
        if options["build"]:
            params["current_build"] = str(options["build"])
        if options["version"]:
            params["current_version"] = options["version"]

        url = reverse("force_update")
        response = client.get(url, params)
        self.stdout.write(response.content.decode())
