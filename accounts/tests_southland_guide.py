from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import SouthlandShowcaseAddon, SouthlandShowcaseInvite, SouthlandShowcaseTheme, User


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

    def test_guide_has_room_recommendation_and_addons(self):
        response = self.client.get(reverse("southland_party_guide"))

        self.assertContains(response, "1–8 Single")
        self.assertContains(response, "9–15 Double")
        self.assertContains(response, "16–25 Triple")
        self.assertContains(response, "26+ Private")
        self.assertContains(response, "Face painting")
        self.assertContains(response, "Professional photographer")

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
