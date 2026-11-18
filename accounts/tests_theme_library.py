from datetime import date

from django.test import TestCase
from django.urls import reverse

from party_summaries.models import PartySummary

from .models import Location, User


class ThemeLibraryAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.get(email="flora@littleamigos.au")
        cls.southland_user = User.objects.get(email="southland@littleamigos.com")
        cls.canberra_user = User.objects.get(email="canberra@littleamigos.com")
        cls.southland = Location.objects.get(code=Location.Code.SOUTHLAND)
        cls.canberra = Location.objects.get(code=Location.Code.CANBERRA)
        cls.southland_photo = cls._summary(
            cls.southland, cls.southland_user, "Frozen", "Southland Customer",
        )
        cls.canberra_photo = cls._summary(
            cls.canberra, cls.canberra_user, "Bluey", "Canberra Customer",
        )

    @classmethod
    def _summary(cls, location, user, theme, owner):
        return PartySummary.objects.create(
            location=location,
            party_date=date(2026, 11, 18),
            party_time="1-3pm",
            owner_name=owner,
            owner_number="0400000000",
            room_type=PartySummary.RoomType.DOUBLE,
            package_name=PartySummary.Package.CUSTOM,
            theme=theme,
            decoration_example=b"finished-party-photo",
            decoration_example_name=f"{theme.lower()}.jpg",
            decoration_example_content_type="image/jpeg",
            created_by=user,
        )

    def test_theme_library_is_first_dashboard_module_for_admin(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard"))

        content = response.content.decode()
        self.assertContains(response, "Theme library")
        self.assertLess(content.index("Theme library"), content.index("Enquiry tracking"))
        self.assertNotContains(response, "Southland showcase")

    def test_admin_chooses_between_both_locations(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("theme_library"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose a location")
        self.assertContains(response, "Little Amigos Southland")
        self.assertContains(response, "Little Amigos Canberra")

    def test_staff_theme_library_redirects_to_own_location(self):
        for user, location in (
            (self.southland_user, self.southland),
            (self.canberra_user, self.canberra),
        ):
            with self.subTest(user=user.email):
                self.client.force_login(user)
                response = self.client.get(reverse("theme_library"))
                self.assertRedirects(
                    response,
                    reverse("theme_library_location", args=(location.code,)),
                    fetch_redirect_response=False,
                )

    def test_staff_cannot_open_other_locations_library(self):
        self.client.force_login(self.southland_user)
        response = self.client.get(
            reverse("theme_library_location", args=(Location.Code.CANBERRA,)),
        )
        self.assertEqual(response.status_code, 404)

    def test_location_library_only_lists_its_own_party_photos(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("theme_library_location", args=(Location.Code.SOUTHLAND,)),
        )

        self.assertContains(response, "Frozen")
        self.assertContains(response, "Southland Customer")
        self.assertNotContains(response, "Bluey")
        self.assertNotContains(response, "Canberra Customer")
        summary = response.context["photos"][0]
        self.assertIn("decoration_example", summary.get_deferred_fields())
        self.assertIn("decoration_reference", summary.get_deferred_fields())
        self.assertIn("invoice_file", summary.get_deferred_fields())

    def test_location_library_searches_theme_and_customer(self):
        self.client.force_login(self.admin)
        url = reverse("theme_library_location", args=(Location.Code.SOUTHLAND,))

        self.assertContains(self.client.get(url, {"search": "Frozen"}), "Southland Customer")
        self.assertContains(self.client.get(url, {"search": "Southland Customer"}), "Frozen")
        self.assertNotContains(self.client.get(url, {"search": "Bluey"}), "Southland Customer")
