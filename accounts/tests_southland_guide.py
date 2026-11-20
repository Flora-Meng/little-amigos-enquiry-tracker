from datetime import date
from decimal import Decimal
import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from party_summaries.models import PartySummary

from .models import Location, SouthlandShowcaseAddon, SouthlandShowcaseInvite, SouthlandShowcaseTheme, SouthlandShowcaseThemePhoto, ThemeLibraryPhoto, User


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
        self.assertContains(response, "1 finger sandwich platter")
        self.assertContains(response, "Nuggets &amp; Chips")
        self.assertContains(response, "package_showcase/southland/food/kids/1.png")
        self.assertContains(response, "package_showcase/southland/food/kids/2.png")
        self.assertNotContains(response, "Kids’ meal photo 3")
        self.assertContains(response, "package_showcase/southland/food/package/1.png", count=4)
        self.assertContains(response, "package_showcase/southland/food/package/11.png", count=4)
        self.assertContains(response, "data-food-carousel")

    def test_guide_has_searchable_theme_catalog(self):
        response = self.client.get(reverse("southland_party_guide"))

        self.assertContains(response, "data-theme-search")
        self.assertContains(response, "Dinosaurs")
        self.assertContains(response, "Mermaid")
        self.assertContains(response, "K-pop Demon Hunters")
        self.assertContains(response, "data-name=\"paw patrol chase marshall skye\"")
        self.assertContains(response, "package_showcase/southland/themes/frozen/01.jpg")
        self.assertNotContains(response, "package_showcase/southland/theme-pages/page-07.jpg")
        self.assertNotContains(response, "Custom Printed Theme")

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
        self.assertContains(response, "package_showcase/southland/addons/cake1.png")
        self.assertContains(response, "package_showcase/southland/addons/cake2.png")
        self.assertContains(response, "package_showcase/southland/addons/photographer.png")
        self.assertContains(response, "package_showcase/southland/addons/partybags.png")
        self.assertNotContains(response, "Not selected")
        self.assertContains(response, "Explore our party food")
        self.assertNotContains(response, "Review your selections")
        self.assertContains(response, "What happens after you choose")
        self.assertContains(response, "Ask Flora a question")
        self.assertContains(response, "Flora will contact you within 24 hours")
        self.assertContains(response, "data-flora-question")
        self.assertNotContains(response, "Ready for the next step?")
        self.assertNotContains(response, "Save the themes and package you love")
        self.assertContains(response, "Around one week before the party")
        self.assertNotContains(response, "Estimated add-on total")
        self.assertContains(response, 'data-package-deposit="$500 deposit"')
        self.assertContains(response, 'data-package-deposit="$1,000 deposit"')

    def test_pdf_package_guides_are_combined_with_package_tabs(self):
        response = self.client.get(reverse("southland_party_guide"))

        self.assertContains(response, "Compare rooms and packages")
        self.assertContains(response, 'data-package-tab="essential"')
        self.assertContains(response, 'data-package-tab="private"')
        self.assertContains(response, 'data-package-panel="essential"')
        self.assertContains(response, "Download full package PDF", count=1)
        self.assertContains(
            response,
            "package_showcase/southland/packages/southland-party-packages.pdf",
        )
        self.assertNotContains(response, "package_showcase/southland/packages/essential.png")
        self.assertNotContains(response, "package_showcase/southland/packages/signature.png")
        self.assertNotContains(response, "package_showcase/southland/packages/ultimate.png")
        self.assertNotContains(response, "package_showcase/southland/packages/private.png")
        self.assertContains(response, "4 adult sharing platters")
        self.assertContains(response, "9 adult sharing platters")
        self.assertContains(response, "12 adult sharing platters")
        self.assertContains(response, "13 adult sharing platters")
        self.assertContains(response, "Exclusive train ride")
        self.assertContains(response, "20-minute mascot appearance", count=2)
        self.assertContains(response, "Party bags for all children")
        self.assertContains(response, "3.5m balloon arch")
        self.assertContains(response, "$38 per child · $16 per adult", count=4)
        self.assertContains(response, "$42 per child · $22 per adult", count=4)
        self.assertNotContains(response, "Single room decoration example")
        self.assertNotContains(response, "data-room-example-tab")
        content = response.content.decode()
        self.assertLess(content.index('id="packages"'), content.index('id="themes"'))
        self.assertLess(content.index('href="#packages"'), content.index('href="#themes"'))

    def test_personalised_guide_shows_enquiry_details(self):
        invite = SouthlandShowcaseInvite.objects.create(
            customer_name="Jorja",
            estimated_guest_count=15,
        )

        response = self.client.get(reverse("southland_party_guide_invite", kwargs={"token": invite.token}))

        self.assertContains(response, "Prepared for Jorja")
        self.assertContains(response, "recommend starting with the Double Room")

    def test_guide_offers_direct_flora_contact(self):
        response = self.client.get(reverse("southland_party_guide"))

        self.assertContains(response, "Party Coordinator — Flora")
        self.assertContains(response, "Email Flora what you would like")
        self.assertContains(response, "Submit question to Flora")
        self.assertContains(response, 'href="tel:0439046887"')
        self.assertContains(response, "0439 046 887")
        self.assertNotContains(response, "Use the personalised party-guide link")

    def test_personalised_guide_saves_customer_choices(self):
        invite = SouthlandShowcaseInvite.objects.create(customer_name="Jorja")

        response = self.client.post(
            reverse("southland_party_guide_invite", kwargs={"token": invite.token}),
            {
                "selected_package": "signature",
                "selected_theme": "Frozen",
                "selected_addons": json.dumps([
                    "Face painting — 1.5 hours",
                    "Party bags × 12",
                ]),
                "customer_question": "Can we bring our own cake?",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("question_sent=1#ask-flora", response.url)
        invite.refresh_from_db()
        self.assertEqual(invite.selected_package, "signature")
        self.assertEqual(invite.selected_theme, "Frozen")
        self.assertEqual(
            invite.selected_addons,
            ["Face painting — 1.5 hours", "Party bags × 12"],
        )
        self.assertEqual(invite.customer_question, "Can we bring our own cake?")
        self.assertIsNone(invite.question_resolved_at)
        self.assertIsNotNone(invite.choices_submitted_at)

        saved_page = self.client.get(response.url)
        self.assertContains(saved_page, 'data-initial-package="signature"')
        self.assertContains(saved_page, 'data-initial-theme="Frozen"')
        self.assertContains(saved_page, "Question sent successfully")

    def test_generic_guide_creates_identified_question_for_flora(self):
        response = self.client.post(
            reverse("southland_party_guide"),
            {
                "selected_package": "ultimate",
                "selected_theme": "Frozen",
                "selected_addons": json.dumps(["Party bags × 8"]),
                "customer_name": "Maya",
                "customer_email": "maya@example.com",
                "customer_phone": "0439000001",
                "customer_question": "Is the date still available?",
            },
        )

        self.assertEqual(response.status_code, 302)
        invite = SouthlandShowcaseInvite.objects.get(customer_name="Maya")
        self.assertIn(str(invite.token), response.url)
        self.assertEqual(invite.email, "maya@example.com")
        self.assertEqual(invite.phone, "0439000001")
        self.assertEqual(invite.selected_package, "ultimate")
        self.assertEqual(invite.selected_theme, "Frozen")
        self.assertEqual(invite.selected_addons, ["Party bags × 8"])
        self.assertEqual(invite.customer_question, "Is the date still available?")

    def test_generic_guide_cannot_save_unidentified_choices(self):
        response = self.client.post(
            reverse("southland_party_guide"),
            {
                "selected_package": "essential",
                "selected_theme": "",
                "selected_addons": "[]",
            },
        )

        self.assertEqual(response.status_code, 400)


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

    def test_manager_lists_customer_choice_submissions(self):
        SouthlandShowcaseInvite.objects.create(
            customer_name="Jorja",
            phone="0439000000",
            selected_package="signature",
            selected_theme="Frozen",
            selected_addons=["Face painting — 1.5 hours"],
            customer_question="Can we arrive early?",
            choices_submitted_at=timezone.now(),
        )

        response = self.client.get(reverse("southland_showcase_manage"))

        self.assertContains(response, "Latest party-guide submissions")
        self.assertContains(response, "Jorja")
        self.assertContains(response, "Signature · Frozen")
        self.assertContains(response, "Face painting — 1.5 hours")
        self.assertContains(response, "Can we arrive early?")

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
                "library_photo": f"summary:{summary.pk}",
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

    def test_direct_theme_library_photo_can_be_applied_to_customer_theme(self):
        library_photo = ThemeLibraryPhoto.objects.create(
            location=Location.objects.get(code=Location.Code.SOUTHLAND),
            theme="Galaxy",
            image_data=b"galaxy-photo",
            image_name="galaxy.jpg",
            image_content_type="image/jpeg",
            created_by=self.admin,
        )
        theme = SouthlandShowcaseTheme.objects.get(name="Dinosaurs")

        response = self.client.post(
            reverse("southland_showcase_update"),
            {
                "action": "apply_summary_photo",
                "library_photo": f"direct:{library_photo.pk}",
                "theme_id": theme.pk,
            },
        )

        self.assertRedirects(response, reverse("southland_showcase_manage"))
        photo = theme.photos.order_by("-pk").first()
        self.assertEqual(bytes(photo.image_data), b"galaxy-photo")
        self.assertIsNone(photo.source_summary)
