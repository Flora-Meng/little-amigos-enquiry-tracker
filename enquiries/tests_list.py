from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from .models import Enquiry, Note


class EnquiryListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.get(email="flora@littleamigos.au")
        cls.southland = User.objects.get(email="southland@littleamigos.com")
        cls.canberra = User.objects.get(email="canberra@littleamigos.com")
        cls.southland_store = Enquiry.objects.create(
            name="Mia Southland",
            phone="0412 111 222",
            email="mia@example.com",
            location=cls.southland.location,
            source=Enquiry.Source.STORE,
            status=Enquiry.Status.NEW,
            party_date=timezone.localdate() + timedelta(days=20),
            submitted_by=cls.southland,
        )
        cls.canberra_store = Enquiry.objects.create(
            name="Leo Canberra",
            phone="0422 333 444",
            location=cls.canberra.location,
            source=Enquiry.Source.STORE,
            status=Enquiry.Status.FOLLOW_UP,
            follow_up_due_date=timezone.localdate() - timedelta(days=1),
            party_date=timezone.localdate() + timedelta(days=10),
            submitted_by=cls.canberra,
        )
        cls.online = Enquiry.objects.create(
            name="Zoe Online",
            email="zoe.online@example.com",
            location=cls.southland.location,
            source=Enquiry.Source.ONLINE,
            status=Enquiry.Status.WAITING_FOR_REPLY,
            follow_up_due_date=timezone.localdate(),
            submitted_by=cls.admin,
            zumo_conversation_id="list-test-online",
        )
        cls.archived = Enquiry.objects.create(
            name="Archived Customer",
            email="archived@example.com",
            location=cls.southland.location,
            source=Enquiry.Source.STORE,
            status=Enquiry.Status.CLOSED,
            archived=True,
            archived_at=timezone.now(),
            submitted_by=cls.admin,
        )

    def test_default_list_excludes_archived(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("enquiry_list"))
        self.assertContains(response, "Mia Southland")
        self.assertContains(response, "Leo Canberra")
        self.assertContains(response, "Zoe Online")
        self.assertNotContains(response, "Archived Customer")

    def test_list_shows_latest_note_and_inline_add_note_form(self):
        Note.objects.create(
            enquiry=self.southland_store,
            body="Older list note",
            author=self.admin,
            author_display_name=self.admin.display_name,
        )
        Note.objects.create(
            enquiry=self.southland_store,
            body="Latest list note",
            author=self.admin,
            author_display_name=self.admin.display_name,
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("enquiry_list"))
        self.assertContains(response, "Latest list note")
        self.assertContains(response, "by Flora")
        self.assertNotContains(response, "Older list note")
        self.assertContains(response, "+ Add note")
        self.assertContains(response, f'id="note-{self.southland_store.id}"')

    def test_note_can_be_added_from_list_and_returns_to_current_filter(self):
        self.client.force_login(self.admin)
        list_url = f'{reverse("enquiry_list")}?source=store'
        response = self.client.post(
            reverse("add_note", args=(self.southland_store.id,)),
            {"body": "Added directly from list", "next": list_url},
        )
        self.assertRedirects(response, list_url)
        self.assertTrue(
            Note.objects.filter(
                enquiry=self.southland_store,
                body="Added directly from list",
                author=self.admin,
            ).exists()
        )

    def test_search_matches_name_phone_and_email(self):
        self.client.force_login(self.admin)
        for term, expected in (
            ("Mia", "Mia Southland"),
            ("333 444", "Leo Canberra"),
            ("zoe.online", "Zoe Online"),
        ):
            with self.subTest(term=term):
                response = self.client.get(reverse("enquiry_list"), {"search": term})
                self.assertContains(response, expected)
                self.assertEqual(response.context["result_count"], 1)

    def test_admin_filters_location_source_status_and_overdue(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("enquiry_list"),
            {
                "location": str(self.canberra.location_id),
                "source": Enquiry.Source.STORE,
                "status": Enquiry.Status.FOLLOW_UP,
                "follow_up": "overdue",
            },
        )
        self.assertContains(response, "Leo Canberra")
        self.assertEqual(response.context["result_count"], 1)

    def test_due_today_filter(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("enquiry_list"), {"follow_up": "due_today"})
        self.assertContains(response, "Zoe Online")
        self.assertNotContains(response, "Leo Canberra")

    def test_archived_only_filter(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("enquiry_list"), {"archived": "only"})
        self.assertContains(response, "Archived Customer")
        self.assertNotContains(response, "Mia Southland")

    def test_staff_query_parameters_cannot_leak_other_location(self):
        self.client.force_login(self.southland)
        response = self.client.get(
            reverse("enquiry_list"),
            {
                "source": Enquiry.Source.ONLINE,
                "location": str(self.canberra.location_id),
                "archived": "all",
            },
        )
        self.assertContains(response, "Mia Southland")
        self.assertContains(response, "Archived Customer")
        self.assertContains(response, "Zoe Online")
        self.assertNotContains(response, "Leo Canberra")

    def test_nearest_party_date_sort_places_null_dates_last(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("enquiry_list"), {"sort": "party_date"})
        names = [enquiry.name for enquiry in response.context["enquiries"]]
        self.assertLess(names.index("Leo Canberra"), names.index("Mia Southland"))
        self.assertLess(names.index("Mia Southland"), names.index("Zoe Online"))
