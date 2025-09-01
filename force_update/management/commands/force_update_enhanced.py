from django.core.management.base import BaseCommand
from django.core.management import CommandError
from force_update.models import ForceUpdateConfig
from force_update.services import get_store_service
from force_update.tasks import fetch_store_versions_task, manual_store_version_update
import json


class Command(BaseCommand):
    help = "Enhanced testing and management command for the force update system"

    def add_arguments(self, parser):
        # Test scenarios
        parser.add_argument(
            "--test-android",
            action="store_true",
            help="Test Android force update scenarios",
        )
        parser.add_argument(
            "--test-ios", action="store_true", help="Test iOS force update scenarios"
        )
        parser.add_argument(
            "--test-all", action="store_true", help="Test all platforms and scenarios"
        )

        # Store API testing
        parser.add_argument(
            "--test-play-store",
            type=str,
            help="Test Google Play Store API with package ID",
        )
        parser.add_argument(
            "--test-app-store", type=str, help="Test Apple App Store API with app ID"
        )

        # Configuration management
        parser.add_argument(
            "--create-config", action="store_true", help="Create default configuration"
        )
        parser.add_argument(
            "--update-from-stores",
            action="store_true",
            help="Update config from app stores",
        )
        parser.add_argument(
            "--show-config", action="store_true", help="Show current configuration"
        )

        # Custom testing
        parser.add_argument(
            "--platform",
            choices=["android", "ios"],
            default="android",
            help="Platform for testing",
        )
        parser.add_argument(
            "--build", type=int, default=0, help="Custom build number for testing"
        )
        parser.add_argument(
            "--app-version",
            type=str,
            default="",
            help="Custom version string for testing",
        )

        # Force update scenarios
        parser.add_argument(
            "--force", action="store_true", help="Test force update scenario"
        )
        parser.add_argument(
            "--optional", action="store_true", help="Test optional update scenario"
        )
        parser.add_argument(
            "--none", action="store_true", help="Test no update scenario"
        )

        # Store configuration
        parser.add_argument(
            "--set-android-package",
            type=str,
            help="Set Android package ID for store fetching",
        )
        parser.add_argument(
            "--set-ios-app-id", type=str, help="Set iOS App Store ID for store fetching"
        )

    def handle(self, *args, **options):
        if options["show_config"]:
            self.show_configuration()

        elif options["create_config"]:
            self.create_default_configuration()

        elif options["test_play_store"]:
            self.test_google_play_store(options["test_play_store"])

        elif options["test_app_store"]:
            self.test_apple_app_store(options["test_app_store"])

        elif options["update_from_stores"]:
            self.update_from_stores()

        elif options["test_android"] or (options["test_all"]):
            self.test_platform_scenarios("android", options)

        elif options["test_ios"] or (options["test_all"]):
            self.test_platform_scenarios("ios", options)

        elif options["set_android_package"]:
            self.set_android_package(options["set_android_package"])

        elif options["set_ios_app_id"]:
            self.set_ios_app_id(options["set_ios_app_id"])

        else:
            # Default behavior - test current platform with provided parameters
            self.test_custom_scenario(options)

    def show_configuration(self):
        """Display current force update configuration."""
        self.stdout.write(self.style.SUCCESS("=== Force Update Configuration ==="))

        try:
            config = ForceUpdateConfig.objects.get(name="production")

            self.stdout.write(f"Name: {config.name}")
            self.stdout.write(f"Platform: {config.platform}")
            self.stdout.write(f"Force Update Enabled: {config.force_update}")
            self.stdout.write(f"Auto Fetch from Stores: {config.auto_fetch_store_info}")

            self.stdout.write(self.style.SUCCESS("\n--- Android Configuration ---"))
            self.stdout.write(
                f"Latest Version: {config.latest_version_name} (Code: {config.latest_version_code})"
            )
            self.stdout.write(
                f"Minimum Required: {config.minimum_required_version_code}"
            )
            self.stdout.write(
                f"Soft Update Threshold: {config.soft_update_version_code}"
            )
            self.stdout.write(f"Play Store URL: {config.play_store_url}")
            self.stdout.write(f"Package ID: {config.android_package_id}")

            self.stdout.write(self.style.SUCCESS("\n--- iOS Configuration ---"))
            self.stdout.write(
                f"Latest Version: {config.ios_latest_version_name} (Build: {config.ios_latest_build_number})"
            )
            self.stdout.write(f"Minimum Required: {config.ios_minimum_required_build}")
            self.stdout.write(f"Soft Update Threshold: {config.ios_soft_update_build}")
            self.stdout.write(f"App Store URL: {config.app_store_url}")
            self.stdout.write(f"App Store ID: {config.ios_app_id}")
            self.stdout.write(f"Bundle ID: {config.ios_bundle_id}")

            self.stdout.write(self.style.SUCCESS("\n--- Store Integration ---"))
            self.stdout.write(f"Last Store Check: {config.last_store_check}")
            self.stdout.write(
                f"Check Interval: {config.store_check_interval_hours} hours"
            )

        except ForceUpdateConfig.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    "No production configuration found. Use --create-config to create one."
                )
            )

    def create_default_configuration(self):
        """Create a default force update configuration."""
        config, created = ForceUpdateConfig.objects.get_or_create(
            name="production",
            defaults={
                "platform": "universal",
                "latest_version_name": "1.0.7",
                "latest_version_code": 7,
                "minimum_required_version_code": 5,
                "soft_update_version_code": 6,
                "force_update": False,
                "auto_fetch_store_info": True,
                "store_check_interval_hours": 24,
                "play_store_url": "https://play.google.com/store/apps/details?id=com.afrobuyug.app",
                "android_package_id": "com.afrobuyug.app",
                "ios_latest_version_name": "1.0.7",
                "ios_latest_build_number": 7,
                "ios_minimum_required_build": 5,
                "ios_soft_update_build": 6,
                "app_store_url": "",
                "ios_app_id": "",
                "ios_bundle_id": "com.afrobuyug.app",
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS("✅ Default configuration created successfully!")
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️ Configuration already exists. Use --show-config to view it."
                )
            )

    def test_google_play_store(self, package_id):
        """Test Google Play Store API."""
        self.stdout.write(
            self.style.SUCCESS(
                f"=== Testing Google Play Store API for {package_id} ==="
            )
        )

        store_service = get_store_service()
        info, error = store_service.get_google_play_version(package_id)

        if info:
            self.stdout.write(
                self.style.SUCCESS("✅ Successfully fetched from Google Play Store:")
            )
            self.stdout.write(json.dumps(info, indent=2))
        else:
            self.stdout.write(
                self.style.ERROR(f"❌ Failed to fetch from Google Play Store: {error}")
            )

    def test_apple_app_store(self, app_id):
        """Test Apple App Store API."""
        self.stdout.write(
            self.style.SUCCESS(
                f"=== Testing Apple App Store API for App ID {app_id} ==="
            )
        )

        store_service = get_store_service()
        info, error = store_service.get_app_store_version(app_id)

        if info:
            self.stdout.write(
                self.style.SUCCESS("✅ Successfully fetched from App Store:")
            )
            self.stdout.write(json.dumps(info, indent=2, default=str))
        else:
            self.stdout.write(
                self.style.ERROR(f"❌ Failed to fetch from App Store: {error}")
            )

    def update_from_stores(self):
        """Update configuration from app stores."""
        self.stdout.write(
            self.style.SUCCESS("=== Updating Configuration from App Stores ===")
        )

        try:
            config = ForceUpdateConfig.objects.get(name="production")

            if config.android_package_id or config.ios_app_id:
                # Trigger the async task
                try:
                    fetch_store_versions_task.delay(config.id)
                    self.stdout.write(
                        self.style.SUCCESS("✅ Store update task queued successfully!")
                    )
                    self.stdout.write(
                        "Check the configuration again in a few moments to see updates."
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️ Async task failed, trying synchronous update: {e}"
                        )
                    )
                    self.sync_update_from_stores(config)
            else:
                self.stdout.write(
                    self.style.ERROR(
                        "❌ No package IDs configured. Use --set-android-package or --set-ios-app-id first."
                    )
                )

        except ForceUpdateConfig.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    "❌ No production configuration found. Use --create-config first."
                )
            )

    def sync_update_from_stores(self, config):
        """Synchronously update from stores."""
        store_service = get_store_service()
        updated = False

        if config.android_package_id:
            self.stdout.write(
                f"Checking Google Play Store for {config.android_package_id}..."
            )
            info, error = store_service.get_google_play_version(
                config.android_package_id
            )
            if info and info.get("version_name"):
                old_version = config.latest_version_name
                config.latest_version_name = info["version_name"]
                self.stdout.write(
                    f"Updated Android version: {old_version} → {config.latest_version_name}"
                )
                updated = True
            elif error:
                self.stdout.write(self.style.ERROR(f"Android update failed: {error}"))

        if config.ios_app_id:
            self.stdout.write(f"Checking App Store for {config.ios_app_id}...")
            info, error = store_service.get_app_store_version(config.ios_app_id)
            if info and info.get("version_name"):
                old_version = config.ios_latest_version_name
                config.ios_latest_version_name = info["version_name"]
                self.stdout.write(
                    f"Updated iOS version: {old_version} → {config.ios_latest_version_name}"
                )
                updated = True
            elif error:
                self.stdout.write(self.style.ERROR(f"iOS update failed: {error}"))

        if updated:
            config.save()
            self.stdout.write(self.style.SUCCESS("✅ Configuration updated and saved!"))
        else:
            self.stdout.write(self.style.WARNING("⚠️ No updates were made."))

    def test_platform_scenarios(self, platform, options):
        """Test force update scenarios for a specific platform."""
        self.stdout.write(
            self.style.SUCCESS(
                f"=== Testing {platform.upper()} Force Update Scenarios ==="
            )
        )

        from django.test import Client
        from django.urls import reverse

        client = Client()
        scenarios = ["force", "optional", "none"]

        for scenario in scenarios:
            params = {
                "platform": platform,
                f"test_{scenario}_update": "true" if scenario != "none" else "true",
            }

            if scenario == "none":
                params = {"platform": platform, "test_no_update": "true"}

            url = reverse("force_update")
            response = client.get(url, params)

            if response.status_code == 200:
                data = response.json()
                self.stdout.write(f"\n--- {scenario.upper()} UPDATE TEST ---")
                self.stdout.write(
                    f"Update Required: {data.get('update_required', False)}"
                )
                self.stdout.write(f"Force Update: {data.get('force_update', False)}")
                self.stdout.write(f"Update Type: {data.get('update_type', 'unknown')}")
                self.stdout.write(f"Message: {data.get('update_message', 'N/A')}")
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ {scenario} test failed with status {response.status_code}"
                    )
                )

    def test_custom_scenario(self, options):
        """Test with custom parameters."""
        platform = options["platform"]
        build = options["build"]
        version = options["app_version"]

        self.stdout.write(self.style.SUCCESS(f"=== Testing Custom Scenario ==="))
        self.stdout.write(f"Platform: {platform}")
        self.stdout.write(f"Build: {build}")
        self.stdout.write(f"Version: {version}")

        from django.test import Client
        from django.urls import reverse

        client = Client()
        params = {"platform": platform}

        if build:
            params["current_build"] = build
        if version:
            params["current_version"] = version

        # Add test scenario flags
        if options["force"]:
            params["test_force_update"] = "true"
        elif options["optional"]:
            params["test_optional_update"] = "true"
        elif options["none"]:
            params["test_no_update"] = "true"

        url = reverse("force_update")
        response = client.get(url, params)

        if response.status_code == 200:
            data = response.json()
            self.stdout.write(self.style.SUCCESS("\n✅ Test Results:"))
            self.stdout.write(json.dumps(data, indent=2, default=str))
        else:
            self.stdout.write(
                self.style.ERROR(f"❌ Test failed with status {response.status_code}")
            )

    def set_android_package(self, package_id):
        """Set Android package ID for store fetching."""
        config, created = ForceUpdateConfig.objects.get_or_create(name="production")
        config.android_package_id = package_id
        config.auto_fetch_store_info = True
        config.save()

        self.stdout.write(
            self.style.SUCCESS(f"✅ Android package ID set to: {package_id}")
        )
        self.stdout.write("Auto-fetch from stores enabled.")

    def set_ios_app_id(self, app_id):
        """Set iOS App Store ID for store fetching."""
        config, created = ForceUpdateConfig.objects.get_or_create(name="production")
        config.ios_app_id = app_id
        config.auto_fetch_store_info = True
        config.save()

        self.stdout.write(self.style.SUCCESS(f"✅ iOS App Store ID set to: {app_id}"))
        self.stdout.write("Auto-fetch from stores enabled.")
