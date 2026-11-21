from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from party_summaries.models import PartySummary

from .models import Location, SouthlandShowcaseInvite, ThemeLibraryPhoto, User


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
        self.assertContains(response, "Party Guide")
        self.assertContains(response, reverse("party_guide_hub"))
        self.assertLess(content.index("Theme library"), content.index("Enquiry tracking"))
        self.assertNotContains(response, "Southland showcase")

    def test_both_staff_dashboards_have_the_party_guide_entry(self):
        for user in (self.southland_user, self.canberra_user):
            with self.subTest(user=user.email):
                self.client.force_login(user)
                response = self.client.get(reverse("dashboard"))
                self.assertContains(response, "Party Guide")
                self.assertContains(response, reverse("party_guide_hub"))

    def test_admin_party_guide_hub_shows_both_locations(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("party_guide_hub"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Little Amigos Southland")
        self.assertContains(response, "Little Amigos Canberra")
        self.assertContains(response, reverse("southland_party_guide"))
        self.assertContains(response, reverse("package_showcase"))

    def test_staff_party_guide_hub_only_shows_own_location(self):
        for user, visible, hidden in (
            (self.southland_user, "Little Amigos Southland", "Little Amigos Canberra"),
            (self.canberra_user, "Little Amigos Canberra", "Little Amigos Southland"),
        ):
            with self.subTest(user=user.email):
                self.client.force_login(user)
                response = self.client.get(reverse("party_guide_hub"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, visible)
                self.assertNotContains(response, hidden)

    def test_anonymous_party_guide_hub_redirects_to_login(self):
        response = self.client.get(reverse("party_guide_hub"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_party_guide_hub_links_to_reply_generator(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("party_guide_hub"))

        self.assertContains(response, "Enquiry reply generator")
        self.assertContains(response, reverse("enquiry_reply_generator"))

    def test_admin_reply_generator_has_both_venues_and_message_versions(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("enquiry_reply_generator"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Little Amigos Southland")
        self.assertContains(response, "Little Amigos Canberra")
        self.assertContains(response, "SMS VERSION")
        self.assertContains(response, "EMAIL VERSION")
        self.assertContains(
            response,
            "https://little-amigos-workplace.onrender.com/party-guide/southland/",
        )
        self.assertContains(
            response,
            "https://little-amigos-workplace.onrender.com/party-guide/canberra/",
        )

    def test_staff_reply_generator_only_offers_own_venue(self):
        for user, visible, hidden in (
            (self.southland_user, "Little Amigos Southland", "Little Amigos Canberra"),
            (self.canberra_user, "Little Amigos Canberra", "Little Amigos Southland"),
        ):
            with self.subTest(user=user.email):
                self.client.force_login(user)
                response = self.client.get(reverse("enquiry_reply_generator"))
                self.assertContains(response, visible)
                self.assertNotContains(response, hidden)

    def test_anonymous_reply_generator_redirects_to_login(self):
        response = self.client.get(reverse("enquiry_reply_generator"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_party_guide_question_is_action_required_for_admin_and_southland(self):
        invite = SouthlandShowcaseInvite.objects.create(
            customer_name="Jorja",
            email="jorja@example.com",
            phone="0439000000",
            selected_package="signature",
            selected_theme="Frozen",
            customer_question="Can we bring our own cake?",
        )
        for user in (self.admin, self.southland_user):
            with self.subTest(user=user.email):
                self.client.force_login(user)
                response = self.client.get(reverse("dashboard"))
                self.assertContains(response, "Action required")
                self.assertContains(response, "Party Guide questions")
                self.assertContains(response, "Can we bring our own cake?")
                self.assertContains(response, "View customer &amp; enquiry details")
                self.assertContains(response, "jorja@example.com")
                self.assertContains(response, "0439000000")
                self.assertContains(response, "Signature")
                self.assertContains(response, "Frozen")
                self.assertContains(
                    response,
                    reverse("southland_question_resolve", args=(invite.pk,)),
                )

        self.client.force_login(self.canberra_user)
        response = self.client.get(reverse("dashboard"))
        self.assertNotContains(response, "Can we bring our own cake?")

    def test_southland_can_mark_party_guide_question_as_handled(self):
        invite = SouthlandShowcaseInvite.objects.create(
            customer_name="Jorja",
            customer_question="Can we bring our own cake?",
        )
        self.client.force_login(self.southland_user)

        response = self.client.post(
            reverse("southland_question_resolve", args=(invite.pk,)),
        )

        self.assertRedirects(response, reverse("dashboard"))
        invite.refresh_from_db()
        self.assertIsNotNone(invite.question_resolved_at)
        response = self.client.get(reverse("dashboard"))
        self.assertNotContains(response, "Can we bring our own cake?")

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

        photos = list(response.context["photos"])
        self.assertEqual([photo.theme for photo in photos], ["Frozen"])
        self.assertEqual([photo.owner_name for photo in photos], ["Southland Customer"])
        self.assertNotContains(response, "Open Party Summary")
        self.assertNotContains(response, "Manage Southland customer showcase")
        self.assertContains(response, "Customer theme catalogue")
        self.assertContains(response, "Choose from uploaded Theme photos")
        summary = photos[0]
        self.assertIn("decoration_example", summary.get_deferred_fields())
        self.assertIn("decoration_reference", summary.get_deferred_fields())
        self.assertIn("invoice_file", summary.get_deferred_fields())

    def test_location_library_searches_theme_and_customer(self):
        self.client.force_login(self.admin)
        url = reverse("theme_library_location", args=(Location.Code.SOUTHLAND,))

        response = self.client.get(url, {"search": "Frozen"})
        self.assertEqual([photo.owner_name for photo in response.context["photos"]], ["Southland Customer"])

        response = self.client.get(url, {"search": "Southland Customer"})
        self.assertEqual([photo.theme for photo in response.context["photos"]], ["Frozen"])

        response = self.client.get(url, {"search": "Bluey"})
        self.assertEqual(list(response.context["photos"]), [])

    def test_staff_can_view_catalogue_but_not_customer_showcase_controls(self):
        self.client.force_login(self.southland_user)
        response = self.client.get(
            reverse("theme_library_location", args=(Location.Code.SOUTHLAND,)),
        )

        self.assertContains(response, "Customer theme catalogue")
        self.assertNotContains(response, "Choose from uploaded Theme photos")
        self.assertNotContains(response, "Add selected photo")

    def test_authorised_user_can_remove_photo_without_deleting_party_summary(self):
        self.client.force_login(self.southland_user)
        response = self.client.post(
            reverse(
                "theme_library_photo_remove",
                args=(Location.Code.SOUTHLAND, self.southland_photo.pk),
            ),
        )

        self.assertRedirects(
            response,
            reverse("theme_library_location", args=(Location.Code.SOUTHLAND,)),
        )
        summary = PartySummary.objects.get(pk=self.southland_photo.pk)
        self.assertIsNone(summary.decoration_example)
        self.assertEqual(summary.decoration_example_name, "")
        self.assertEqual(summary.decoration_example_content_type, "")

    def test_staff_cannot_remove_another_locations_photo(self):
        self.client.force_login(self.southland_user)
        response = self.client.post(
            reverse(
                "theme_library_photo_remove",
                args=(Location.Code.CANBERRA, self.canberra_photo.pk),
            ),
        )

        self.assertEqual(response.status_code, 404)
        self.canberra_photo.refresh_from_db()
        self.assertEqual(bytes(self.canberra_photo.decoration_example), b"finished-party-photo")

    def test_staff_can_create_read_update_and_delete_direct_library_photo(self):
        self.client.force_login(self.southland_user)
        library_url = reverse(
            "theme_library_location",
            args=(Location.Code.SOUTHLAND,),
        )

        response = self.client.post(
            reverse("theme_library_photo_create", args=(Location.Code.SOUTHLAND,)),
            {
                "theme": "Space Party",
                "description": "Blue and silver",
                "image": SimpleUploadedFile(
                    "space.jpg", b"space-image", content_type="image/jpeg",
                ),
            },
        )
        self.assertRedirects(response, library_url)
        photo = ThemeLibraryPhoto.objects.get(theme="Space Party")
        self.assertEqual(photo.location, self.southland)

        response = self.client.get(library_url)
        self.assertContains(response, "Space Party")
        self.assertContains(response, "Blue and silver")
        image_response = self.client.get(
            reverse(
                "theme_library_direct_photo",
                args=(Location.Code.SOUTHLAND, photo.pk),
            ),
        )
        self.assertEqual(image_response.content, b"space-image")

        response = self.client.post(
            reverse(
                "theme_library_direct_photo_update",
                args=(Location.Code.SOUTHLAND, photo.pk),
            ),
            {
                "theme": "Galaxy Party",
                "description": "Purple and silver",
                "image": SimpleUploadedFile(
                    "galaxy.webp", b"galaxy-image", content_type="image/webp",
                ),
            },
        )
        self.assertRedirects(response, library_url)
        photo.refresh_from_db()
        self.assertEqual(photo.theme, "Galaxy Party")
        self.assertEqual(photo.description, "Purple and silver")
        self.assertEqual(bytes(photo.image_data), b"galaxy-image")

        response = self.client.post(
            reverse(
                "theme_library_direct_photo_remove",
                args=(Location.Code.SOUTHLAND, photo.pk),
            ),
        )
        self.assertRedirects(response, library_url)
        self.assertFalse(ThemeLibraryPhoto.objects.filter(pk=photo.pk).exists())

    def test_summary_library_photo_can_be_renamed_and_replaced(self):
        self.client.force_login(self.southland_user)
        response = self.client.post(
            reverse(
                "theme_library_summary_photo_update",
                args=(Location.Code.SOUTHLAND, self.southland_photo.pk),
            ),
            {
                "theme": "Frozen Castle",
                "image": SimpleUploadedFile(
                    "castle.png", b"castle-image", content_type="image/png",
                ),
            },
        )

        self.assertRedirects(
            response,
            reverse("theme_library_location", args=(Location.Code.SOUTHLAND,)),
        )
        self.southland_photo.refresh_from_db()
        self.assertEqual(self.southland_photo.theme, "Frozen Castle")
        self.assertEqual(bytes(self.southland_photo.decoration_example), b"castle-image")
