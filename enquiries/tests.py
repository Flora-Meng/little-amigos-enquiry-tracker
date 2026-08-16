from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from .models import Enquiry


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
