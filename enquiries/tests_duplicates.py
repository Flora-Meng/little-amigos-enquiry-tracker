from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Enquiry
from .services import find_duplicates, normalise_email, normalise_phone


class DuplicateDetectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.get(email="flora@littleamigos.au")
        cls.southland = User.objects.get(email="southland@littleamigos.com")
        cls.canberra = User.objects.get(email="canberra@littleamigos.com")
        cls.existing = Enquiry.objects.create(
            name="Existing Customer",
            phone="+61 412 345 678",
            email="Customer@Example.COM ",
            location=cls.southland.location,
            source=Enquiry.Source.STORE,
            status=Enquiry.Status.NEW,
            submitted_by=cls.southland,
        )
        cls.private_online = Enquiry.objects.create(
            name="Private Online Match",
            phone="0400 777 888",
            location=cls.southland.location,
            source=Enquiry.Source.ONLINE,
            status=Enquiry.Status.NEW,
            submitted_by=cls.admin,
            zumo_conversation_id="duplicate-private-online",
        )
        cls.other_store = Enquiry.objects.create(
            name="Other Store Match",
            email="other@example.com",
            location=cls.canberra.location,
            source=Enquiry.Source.STORE,
            status=Enquiry.Status.NEW,
            submitted_by=cls.canberra,
        )

    def test_contact_normalisation_handles_case_spacing_and_australian_prefix(self):
        self.assertEqual(normalise_email(" Test@Example.COM "), "test@example.com")
        self.assertEqual(normalise_phone("+61 412 345 678"), "0412345678")
        self.assertEqual(normalise_phone("0412 345 678"), "0412345678")

    def test_duplicate_service_matches_either_phone_or_email(self):
        by_phone = find_duplicates(Enquiry.objects.all(), phone="0412 345 678")
        by_email = find_duplicates(Enquiry.objects.all(), email="customer@example.com")
        self.assertEqual(list(by_phone), [self.existing])
        self.assertEqual(list(by_email), [self.existing])

    def test_warning_does_not_create_until_user_confirms(self):
        self.client.force_login(self.southland)
        payload = {
            "name": "Repeat Party",
            "phone": "0412 345 678",
            "party_date_unknown": "on",
        }
        warning = self.client.post(reverse("new_store_enquiry"), payload)
        self.assertEqual(warning.status_code, 200)
        self.assertContains(warning, "Possible duplicate")
        self.assertContains(warning, "Existing Customer")
        self.assertFalse(Enquiry.objects.filter(name="Repeat Party").exists())

        payload["confirm_duplicate"] = "1"
        confirmed = self.client.post(reverse("new_store_enquiry"), payload)
        self.assertRedirects(confirmed, reverse("dashboard"))
        self.assertTrue(Enquiry.objects.filter(name="Repeat Party").exists())

    def test_staff_duplicate_warning_does_not_expose_online_or_other_store(self):
        self.client.force_login(self.southland)
        online_response = self.client.post(
            reverse("new_store_enquiry"),
            {"name": "Online Collision", "phone": "0400 777 888"},
        )
        other_response = self.client.post(
            reverse("new_store_enquiry"),
            {"name": "Store Collision", "email": "other@example.com"},
        )
        self.assertEqual(online_response.status_code, 302)
        self.assertEqual(other_response.status_code, 302)
        self.assertNotIn(b"Private Online Match", online_response.content)
        self.assertNotIn(b"Other Store Match", other_response.content)
        self.assertTrue(Enquiry.objects.filter(name="Online Collision").exists())
        self.assertTrue(Enquiry.objects.filter(name="Store Collision").exists())

    def test_admin_duplicate_warning_can_link_all_authorised_matches(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("new_store_enquiry"),
            {
                "name": "Admin Collision",
                "phone": "0400 777 888",
                "location": str(self.southland.location_id),
            },
        )
        self.assertContains(response, "Private Online Match")
