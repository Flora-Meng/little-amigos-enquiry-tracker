from datetime import date
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from party_summaries.models import PartySummary

from .models import Location, SouthlandShowcaseAddon, SouthlandShowcaseInvite, SouthlandShowcaseTheme, SouthlandShowcaseThemePhoto, User


class SouthlandPartyGuideTests(TestCase):
    def test_public_guide_does_not_require_login(self):
        response = self.client.get(reverse("southland_party_guide"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Southland Party Guide")
        self.assertContains(response, "One place to plan their best day")

    def test_guide_lists_current_packages_and_menu_inclusions(self):
        response = self.client.get(reverse("southland_party_guide"))

        self.assertContains(response, "Essential package")
        self.assertContains(response, "$699")
        self.assertContains(response, "$899")
        self.assertContains(response, "Signature package")
        self.assertContains(response, "$999")
        self.assertContains(response, "$1,299")
        self.assertContains(response, "Ultimate package")
        self.assertContains(response, "$1,899")
        self.assertContains(response, "$2,199")
        self.assertContains(response, "Private package")
        self.assertContains(response, "$2,699")
        self.assertContains(response, "$2,999")
        self.assertContains(response, "Kids' menu")
        self.assertContains(response, "One finger sandwich platter")

    def test_guide_has_searchable_theme_catalog(self):
        response = self.client.get(reverse("southland_party_guide"))

        self.assertContains(response, "data-theme-search")
        self.assertContains(response, "Dinosaurs")
        self.assertContains(response, "Mermaid")
        self.assertContains(response, "Custom Printed Theme")
        self.assertContains(response, "K-pop Demon Hunters")
        self.assertContains(response, "data-name=\"paw patrol chase marshall skye\"")

    def test_permanent_theme_list_is_public_and_uses_current_catalog(self):
        response = self.client.get(reverse("southland_theme_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Southland Theme List")
        self.assertContains(response, "Dinosaurs")
        self.assertContains(response, "data-theme-search")

    def test_guide_has_room_recommendation_and_addons(self):
        response = self.client.get(reverse("southland_party_guide"))

        self.assertContains(response, "1–8 Single")
        self.assertContains(response, "9–15 Double")
        self.assertContains(response, "16–25 Triple")
        self.assertContains(response, "26+ Private")
        self.assertContains(response, "Face painting")
        self.assertContains(response, "Professional photographer")

    def test_addons_have_selectable_variants_and_quantity(self):
        response = self.client.get(reverse("southland_party_guide"))

        self.assertContains(response, "Face painting — 1.5 hours")
        self.assertContains(response, "Entertainer or mascot — 2 hours")
        self.assertContains(response, "Tall 6+8 two-tier cake")
        self.assertContains(response, "Professional photographer — 2 hours")
        self.assertContains(response, "data-addon-quantity")
        self.assertContains(response, 'data-unit-price="8"')

    def test_room_examples_are_combined_with_package_tabs(self):
        response = self.client.get(reverse("southland_party_guide"))

        self.assertContains(response, "Compare rooms and packages")
        self.assertContains(response, 'data-package-tab="essential"')
        self.assertContains(response, 'data-package-tab="private"')
        self.assertContains(response, 'data-package-panel="essential"')
        self.assertContains(response, "Single room decoration example")
        self.assertNotContains(response, "data-room-example-tab")

    def test_personalised_guide_shows_enquiry_details(self):
        invite = SouthlandShowcaseInvite.objects.create(
            customer_name="Jorja",
            estimated_guest_count=15,
        )

        response = self.client.get(reverse("southland_party_guide_invite", kwargs={"token": invite.token}))

        self.assertContains(response, "Prepared for Jorja")
        self.assertContains(response, "recommend starting with the Double Room")


class SouthlandShowcaseManagerTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin-showcase@example.com",
            display_name="Admin",
            password="password",
            role=User.Role.ADMIN,
            password_reset_required=False,
        )
        self.client.force_login(self.admin)

    def test_admin_can_open_manager(self):
        response = self.client.get(reverse("southland_showcase_manage"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manage themes and add-ons")

    def test_admin_can_add_theme_with_image(self):
        response = self.client.post(
            reverse("southland_showcase_update"),
            {
                "action": "add_theme",
                "name": "Space Party",
                "category": "adventure",
                "search_terms": "galaxy astronaut",
                "image": SimpleUploadedFile("space.jpg", b"fake-jpeg", content_type="image/jpeg"),
            },
        )

        self.assertRedirects(response, reverse("southland_showcase_manage"))
        theme = SouthlandShowcaseTheme.objects.get(name="Space Party")
        self.assertEqual(theme.photos.count(), 1)

    def test_admin_can_hide_addon(self):
        addon = SouthlandShowcaseAddon.objects.get(name="Face painting")
        self.client.post(
            reverse("southland_showcase_update"),
            {"action": "toggle_addon", "addon_id": addon.pk},
        )

        addon.refresh_from_db()
        self.assertFalse(addon.is_active)

    def test_party_summary_photo_appears_in_library_and_can_be_applied(self):
        summary = PartySummary.objects.create(
            location=Location.objects.get(code=Location.Code.SOUTHLAND),
            party_date=date(2026, 12, 12),
            party_time="1-3pm",
            owner_name="Tom",
            owner_number="0423683136",
            room_type=PartySummary.RoomType.DOUBLE,
            kids_count=12,
            adults_count=16,
            kids_name="Sam",
            theme="Bluey",
            decoration_example=b"party-photo",
            decoration_example_name="bluey.jpg",
            decoration_example_content_type="image/jpeg",
            package_name=PartySummary.Package.DOUBLE_WEEKEND,
            package_amount=Decimal("1299.00"),
            created_by=self.admin,
        )
        manager = self.client.get(reverse("southland_showcase_manage"))
        self.assertContains(manager, "Photos from Party Summaries")
        self.assertContains(manager, "Bluey")
        self.assertContains(manager, "Tom")

        theme = SouthlandShowcaseTheme.objects.get(name="Dinosaurs")
        response = self.client.post(
            reverse("southland_showcase_update"),
            {
                "action": "apply_summary_photo",
                "summary_id": summary.pk,
                "theme_id": theme.pk,
            },
        )
        self.assertRedirects(response, reverse("southland_showcase_manage"))
        photo = SouthlandShowcaseThemePhoto.objects.get(
            theme=theme, source_summary=summary,
        )
        self.assertEqual(bytes(photo.image_data), b"party-photo")

    def test_admin_can_create_theme_from_party_summary_photo(self):
        summary = PartySummary.objects.create(
            location=Location.objects.get(code=Location.Code.SOUTHLAND),
            party_date=date(2027, 1, 9),
            party_time="10-12",
            owner_name="Mia",
            owner_number="0400000000",
            room_type=PartySummary.RoomType.SINGLE,
            theme="Rainbow Garden",
            decoration_example=b"rainbow-photo",
            decoration_example_name="rainbow.webp",
            decoration_example_content_type="image/webp",
            package_name=PartySummary.Package.SINGLE_WEEKEND,
            package_amount=Decimal("899.00"),
            created_by=self.admin,
        )
        response = self.client.post(
            reverse("southland_showcase_update"),
            {
                "action": "create_theme_from_summary",
                "summary_id": summary.pk,
                "name": "Rainbow Garden",
            },
        )

        self.assertRedirects(response, reverse("southland_showcase_manage"))
        theme = SouthlandShowcaseTheme.objects.get(name="Rainbow Garden")
        self.assertTrue(theme.is_active)
        self.assertEqual(theme.photos.get().source_summary, summary)
