from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Enquiry, Note


class NewStoreEnquiryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.get(email="flora@littleamigos.au")
        cls.southland = User.objects.get(email="southland@littleamigos.com")
        cls.canberra = User.objects.get(email="canberra@littleamigos.com")

    def test_login_is_required(self):
        response = self.client.get(reverse("new_store_enquiry"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('new_store_enquiry')}",
        )

    def test_staff_form_does_not_expose_location_selector(self):
        self.client.force_login(self.southland)
        response = self.client.get(reverse("new_store_enquiry"))
        self.assertNotContains(response, 'name="location"')
        self.assertContains(response, "Little Amigos Southland")

    def test_staff_submission_forces_own_location_and_store_new_values(self):
        self.client.force_login(self.southland)
        response = self.client.post(
            reverse("new_store_enquiry"),
            {
                "name": "Ava Customer",
                "phone": "0412 345 678",
                "postcode": "3192",
                "party_date_unknown": "on",
                "initial_note": "Customer called the Southland store.",
                "location": str(self.canberra.location_id),
                "source": Enquiry.Source.ONLINE,
                "status": Enquiry.Status.BOOKED,
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        enquiry = Enquiry.objects.get(name="Ava Customer")
        self.assertEqual(enquiry.location, self.southland.location)
        self.assertEqual(enquiry.source, Enquiry.Source.STORE)
        self.assertEqual(enquiry.status, Enquiry.Status.NEW)
        self.assertEqual(enquiry.submitted_by, self.southland)
        note = Note.objects.get(enquiry=enquiry)
        self.assertEqual(note.body, "Customer called the Southland store.")
        self.assertEqual(note.author_display_name, "Kiva")

    def test_admin_can_choose_location(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("new_store_enquiry"),
            {
                "name": "Noah Customer",
                "email": "noah@example.com",
                "postcode": "2601",
                "party_date": "2027-02-20",
                "location": str(self.canberra.location_id),
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        enquiry = Enquiry.objects.get(name="Noah Customer")
        self.assertEqual(enquiry.location, self.canberra.location)
        self.assertEqual(enquiry.submitted_by, self.admin)

    def test_phone_or_email_is_required(self):
        self.client.force_login(self.southland)
        response = self.client.post(
            reverse("new_store_enquiry"),
            {"name": "Missing Contact", "postcode": "3192"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Provide at least a phone number or email address")
        self.assertFalse(Enquiry.objects.filter(name="Missing Contact").exists())

    def test_party_date_and_not_sure_cannot_both_be_selected(self):
        self.client.force_login(self.southland)
        response = self.client.post(
            reverse("new_store_enquiry"),
            {
                "name": "Date Conflict",
                "phone": "0400 111 222",
                "party_date": "2027-04-10",
                "party_date_unknown": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose a date or Not sure yet, not both")
        self.assertFalse(Enquiry.objects.filter(name="Date Conflict").exists())
