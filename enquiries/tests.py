from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from .models import Enquiry, Note


class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.get(email="flora@littleamigos.au")
        cls.southland = User.objects.get(email="southland@littleamigos.com")
        cls.canberra = User.objects.get(email="canberra@littleamigos.com")
        for user in (cls.admin, cls.southland, cls.canberra):
            user.set_password("Test-only strong password 47!")
            user.save()

        cls.southland_store = Enquiry.objects.create(
            name="Southland Store Customer",
            phone="0400 000 001",
            location=cls.southland.location,
            source=Enquiry.Source.STORE,
            status=Enquiry.Status.NEW,
            submitted_by=cls.southland,
        )
        cls.canberra_store = Enquiry.objects.create(
            name="Canberra Store Customer",
            email="canberra.customer@example.com",
            location=cls.canberra.location,
            source=Enquiry.Source.STORE,
            status=Enquiry.Status.BOOKED,
            booking_amount_aud=Decimal("450.00"),
            submitted_by=cls.canberra,
        )
        cls.online = Enquiry.objects.create(
            name="Private Online Customer",
            email="online.customer@example.com",
            location=cls.southland.location,
            source=Enquiry.Source.ONLINE,
            status=Enquiry.Status.WAITING_FOR_REPLY,
            follow_up_due_date=timezone.localdate() + timedelta(days=2),
            submitted_by=cls.admin,
            zumo_conversation_id="test-conversation-1",
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_email_password_login_and_logout(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.admin.email, "password": "Test-only strong password 47!"},
        )
        self.assertRedirects(response, reverse("dashboard"))
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))

    def test_admin_dashboard_has_cross_location_summary(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Southland Store Customer")
        self.assertContains(response, "Canberra Store Customer")
        self.assertContains(response, "Private Online Customer")
        self.assertContains(response, "$450.00")
        self.assertContains(response, 'name="status"')

    def test_dashboard_shows_latest_note(self):
        Note.objects.create(
            enquiry=self.southland_store,
            body="First conversation note",
            author=self.admin,
            author_display_name=self.admin.display_name,
        )
        Note.objects.create(
            enquiry=self.southland_store,
            body="Latest dashboard note",
            author=self.admin,
            author_display_name=self.admin.display_name,
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Latest dashboard note")
        self.assertContains(response, "by Flora")
        self.assertNotContains(response, "First conversation note")

    def test_admin_can_change_status_from_dashboard(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("quick_update_status", args=(self.southland_store.id,)),
            {"status": Enquiry.Status.CONTACTED},
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.southland_store.refresh_from_db()
        self.assertEqual(self.southland_store.status, Enquiry.Status.CONTACTED)

    def test_admin_can_change_status_from_all_enquiries_and_stay_on_list(self):
        self.client.force_login(self.admin)
        list_url = f'{reverse("enquiry_list")}?source=store'
        response = self.client.get(list_url)
        self.assertContains(response, 'name="status"')
        response = self.client.post(
            reverse("quick_update_status", args=(self.southland_store.id,)),
            {"status": Enquiry.Status.CONTACTED, "next": list_url},
        )
        self.assertRedirects(response, list_url)
        self.southland_store.refresh_from_db()
        self.assertEqual(self.southland_store.status, Enquiry.Status.CONTACTED)

    def test_booked_status_redirects_for_required_booking_amount(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("quick_update_status", args=(self.southland_store.id,)),
            {"status": Enquiry.Status.BOOKED},
        )
        self.assertRedirects(
            response,
            reverse("enquiry_detail", args=(self.southland_store.id,)),
        )
        self.southland_store.refresh_from_db()
        self.assertEqual(self.southland_store.status, Enquiry.Status.NEW)

    def test_closed_status_can_be_selected_without_reason(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("quick_update_status", args=(self.southland_store.id,)),
            {"status": Enquiry.Status.CLOSED},
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.southland_store.refresh_from_db()
        self.assertEqual(self.southland_store.status, Enquiry.Status.CLOSED)
        self.assertEqual(self.southland_store.closed_reason, "")

    def test_staff_cannot_change_status_from_dashboard(self):
        self.client.force_login(self.southland)
        response = self.client.post(
            reverse("quick_update_status", args=(self.southland_store.id,)),
            {"status": Enquiry.Status.CONTACTED},
        )
        self.assertEqual(response.status_code, 403)
        self.southland_store.refresh_from_db()
        self.assertEqual(self.southland_store.status, Enquiry.Status.NEW)

    def test_staff_dashboard_never_receives_online_or_other_location_rows(self):
        self.client.force_login(self.southland)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Southland Store Customer")
        self.assertNotContains(response, "Canberra Store Customer")
        self.assertNotContains(response, "Private Online Customer")

    def test_canberra_staff_only_receives_canberra_store_rows(self):
        self.client.force_login(self.canberra)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Canberra Store Customer")
        self.assertNotContains(response, "Southland Store Customer")
        self.assertNotContains(response, "Private Online Customer")
