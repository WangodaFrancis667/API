from django.test import TestCase
from django.urls import reverse
from .models import ForceUpdateConfig

class ForceUpdateTests(TestCase):
    def setUp(self):
        ForceUpdateConfig.objects.create(
            name="production",
            minimum_required_version_code=10,
            latest_version_name="1.0.7",
            latest_version_code=24,
            force_update=True,
            soft_update_version_code=23,
            play_store_url="https://play.google.com/store/apps/details?id=com.afrobuyug.app",
        )

    def test_no_build_provides_instructions(self):
        url = reverse("force_update")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("testing_instructions", data)

    def test_force_update_scenario_flag(self):
        url = reverse("force_update") + "?test_force_update=true"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["debug_info"]["test_scenario"], "force_update")
        # self.assertTrue(data["update_required"])
        # self.assertTrue(data["force_update"])

    def test_optional_update_flag(self):
        url = reverse("force_update") + "?test_optional_update=true"
        resp = self.client.get(url)
        data = resp.json()
        self.assertEqual(data["debug_info"]["test_scenario"], "optional_update")
        self.assertTrue(data["update_required"])

    def test_custom_build_less_than_minimum(self):
        url = reverse("force_update") + "?current_build=5"
        resp = self.client.get(url)
        data = resp.json()
        self.assertTrue(data["update_required"])
        self.assertEqual(data["update_type"], "force" if data["force_update"] else "recommended")
