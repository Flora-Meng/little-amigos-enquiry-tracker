from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class PackageShowcaseAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.get(email="flora@littleamigos.au")
        cls.southland = User.objects.get(email="southland@littleamigos.com")
        cls.canberra = User.objects.get(email="canberra@littleamigos.com")

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("package_showcase"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_canberra_and_admin_can_open_showcase(self):
        for user in (self.canberra, self.admin):
            with self.subTest(user=user.email):
                self.client.force_login(user)
                response = self.client.get(reverse("package_showcase"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Canberra package showcase")
                self.assertContains(response, "Double · Weekday")
                self.assertContains(response, "Private · 3 hours")
                self.assertContains(response, "Face painting")
                self.assertContains(response, "6+8 two-tier cake")
                self.assertContains(response, "Tall 6+8 two-tier cake")
                self.assertContains(response, "Custom theme")
                self.assertContains(response, 'data-addon-price="250"')
                self.assertContains(response, "package_showcase/canberra/double-room-1-20261009.jpg", count=2)
                self.assertContains(response, "package_showcase/canberra/private-1.jpg", count=2)
                self.assertNotContains(response, "Single (voucher)")

    def test_southland_account_cannot_open_canberra_showcase(self):
        self.client.force_login(self.southland)
        self.assertEqual(self.client.get(reverse("package_showcase")).status_code, 404)
