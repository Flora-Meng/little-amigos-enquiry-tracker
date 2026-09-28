from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from .models import Enquiry, Note


class EnquiryDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.get(email="flora@littleamigos.au")
        cls.southland = User.objects.get(email="southland@littleamigos.com")
        cls.canberra = User.objects.get(email="canberra@littleamigos.com")
        cls.store = Enquiry.objects.create(
            name="Detail Customer",
            phone="0400 555 111",
            email="detail@example.com",
            postcode="3192",
            location=cls.southland.location,
            source=Enquiry.Source.STORE,
            status=Enquiry.Status.NEW,
            submitted_by=cls.southland,
        )
        cls.online = Enquiry.objects.create(
            name="Online Secret",
            email="secret@example.com",
            location=cls.southland.location,
            source=Enquiry.Source.ONLINE,
            status=Enquiry.Status.NEW,
            submitted_by=cls.admin,
            zumo_conversation_id="detail-online",
        )

    def update_payload(self, **changes):
        payload = {
            "name": self.store.name,
            "phone": self.store.phone,
            "email": self.store.email,
            "postcode": self.store.postcode,
            "party_date": "",
            "location": str(self.store.location_id),
            "status": self.store.status,
            "follow_up_due_date": "",
            "booking_amount_aud": "",
            "closed_reason": "",
            "closed_reason_details": "",
        }
        payload.update(changes)
        return payload

    def test_admin_sees_edit_and_archive_actions(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("enquiry_detail", args=(self.store.id,)))
        self.assertContains(response, "Edit enquiry")
        self.assertContains(response, '<section class="panel edit-panel">')
        self.assertNotContains(response, '<details class="panel edit-panel"')
        self.assertContains(response, "Archive")

    def test_staff_sees_own_store_detail_but_not_admin_controls(self):
        self.client.force_login(self.southland)
        response = self.client.get(reverse("enquiry_detail", args=(self.store.id,)))
        self.assertContains(response, "Detail Customer")
        self.assertNotContains(response, "Edit enquiry")
        self.assertNotContains(response, reverse("update_enquiry", args=(self.store.id,)))
        self.assertNotContains(response, ">Archive<")

    def test_staff_cannot_guess_online_or_other_location_detail_url(self):
        self.client.force_login(self.southland)
        online_response = self.client.get(reverse("enquiry_detail", args=(self.online.id,)))
        self.assertEqual(online_response.status_code, 404)
        self.client.force_login(self.canberra)
        store_response = self.client.get(reverse("enquiry_detail", args=(self.store.id,)))
        self.assertEqual(store_response.status_code, 404)

    def test_staff_direct_update_and_archive_posts_are_rejected(self):
        self.client.force_login(self.southland)
        update_response = self.client.post(
            reverse("update_enquiry", args=(self.store.id,)),
            self.update_payload(name="Tampered", status=Enquiry.Status.BOOKED, booking_amount_aud="1"),
        )
        archive_response = self.client.post(reverse("archive_enquiry", args=(self.store.id,)))
        self.assertEqual(update_response.status_code, 403)
        self.assertEqual(archive_response.status_code, 403)
        self.store.refresh_from_db()
        self.assertEqual(self.store.name, "Detail Customer")
        self.assertFalse(self.store.archived)

    def test_waiting_and_follow_up_schedule_two_calendar_days(self):
        self.client.force_login(self.admin)
        for status in (Enquiry.Status.WAITING_FOR_REPLY, Enquiry.Status.FOLLOW_UP):
            with self.subTest(status=status):
                self.store.status = Enquiry.Status.NEW
                self.store.follow_up_due_date = None
                self.store.save()
                response = self.client.post(
                    reverse("update_enquiry", args=(self.store.id,)),
                    self.update_payload(status=status, follow_up_due_date="2035-01-01"),
                )
                self.assertRedirects(response, reverse("enquiry_detail", args=(self.store.id,)))
                self.store.refresh_from_db()
                self.assertEqual(self.store.follow_up_due_date, timezone.localdate() + timedelta(days=2))

    def test_booked_requires_amount_and_clears_follow_up(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("update_enquiry", args=(self.store.id,)),
            self.update_payload(status=Enquiry.Status.BOOKED),
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Enter the booking amount in AUD", status_code=400)

        response = self.client.post(
            reverse("update_enquiry", args=(self.store.id,)),
            self.update_payload(
                status=Enquiry.Status.BOOKED,
                booking_amount_aud="675.50",
                follow_up_due_date="2035-01-01",
            ),
        )
        self.assertEqual(response.status_code, 302)
        self.store.refresh_from_db()
        self.assertEqual(self.store.booking_amount_aud, Decimal("675.50"))
        self.assertIsNone(self.store.follow_up_due_date)

    def test_closed_reason_is_optional_but_other_still_requires_details(self):
        self.client.force_login(self.admin)
        url = reverse("update_enquiry", args=(self.store.id,))
        no_reason = self.client.post(url, self.update_payload(status=Enquiry.Status.CLOSED))
        self.assertRedirects(no_reason, reverse("enquiry_detail", args=(self.store.id,)))
        self.store.refresh_from_db()
        self.assertEqual(self.store.status, Enquiry.Status.CLOSED)
        self.assertEqual(self.store.closed_reason, "")

        self.store.status = Enquiry.Status.NEW
        self.store.save(update_fields=("status", "updated_at"))
        no_details = self.client.post(
            url,
            self.update_payload(status=Enquiry.Status.CLOSED, closed_reason=Enquiry.ClosedReason.OTHER),
        )
        self.assertEqual(no_details.status_code, 400)
        valid = self.client.post(
            url,
            self.update_payload(
                status=Enquiry.Status.CLOSED,
                closed_reason=Enquiry.ClosedReason.OTHER,
                closed_reason_details="Customer moved interstate.",
                follow_up_due_date="2035-01-01",
            ),
        )
        self.assertEqual(valid.status_code, 302)
        self.store.refresh_from_db()
        self.assertEqual(self.store.closed_reason_details, "Customer moved interstate.")
        self.assertIsNone(self.store.follow_up_due_date)

    def test_admin_and_relevant_staff_can_append_notes(self):
        url = reverse("add_note", args=(self.store.id,))
        self.client.force_login(self.southland)
        self.client.post(url, {"body": "Staff note"})
        self.client.force_login(self.admin)
        self.client.post(url, {"body": "Admin note"})
        notes = list(Note.objects.filter(enquiry=self.store).order_by("created_at"))
        self.assertEqual([note.body for note in notes], ["Staff note", "Admin note"])
        self.assertEqual([note.author_display_name for note in notes], ["Kiva", "Flora"])

    def test_staff_cannot_add_note_to_online_enquiry(self):
        self.client.force_login(self.southland)
        response = self.client.post(reverse("add_note", args=(self.online.id,)), {"body": "Leak"})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Note.objects.filter(body="Leak").exists())

    def test_notes_cannot_be_edited_but_can_be_deleted(self):
        note = Note.objects.create(
            enquiry=self.store,
            body="Permanent note",
            author=self.admin,
            author_display_name="Flora",
        )
        note.body = "Rewritten"
        with self.assertRaisesMessage(Exception, "append-only"):
            note.save()
        self.assertTrue(Note.objects.filter(id=note.id, body="Permanent note").exists())
        note.delete()
        self.assertFalse(Note.objects.filter(id=note.id).exists())

    def test_admin_can_delete_any_note(self):
        note = Note.objects.create(
            enquiry=self.store,
            body="Staff note to remove",
            author=self.southland,
            author_display_name=self.southland.display_name,
        )
        self.client.force_login(self.admin)
        response = self.client.post(reverse("delete_note", args=(note.id,)))
        self.assertRedirects(response, reverse("enquiry_detail", args=(self.store.id,)))
        self.assertFalse(Note.objects.filter(id=note.id).exists())

    def test_staff_can_delete_own_note_but_not_someone_elses(self):
        own_note = Note.objects.create(
            enquiry=self.store,
            body="Kiva own note",
            author=self.southland,
            author_display_name=self.southland.display_name,
        )
        admin_note = Note.objects.create(
            enquiry=self.store,
            body="Flora note",
            author=self.admin,
            author_display_name=self.admin.display_name,
        )
        self.client.force_login(self.southland)
        denied = self.client.post(reverse("delete_note", args=(admin_note.id,)))
        self.assertEqual(denied.status_code, 403)
        self.assertTrue(Note.objects.filter(id=admin_note.id).exists())

        allowed = self.client.post(reverse("delete_note", args=(own_note.id,)))
        self.assertRedirects(allowed, reverse("enquiry_detail", args=(self.store.id,)))
        self.assertFalse(Note.objects.filter(id=own_note.id).exists())

    def test_admin_archive_preserves_record_and_notes(self):
        Note.objects.create(
            enquiry=self.store,
            body="Keep this note",
            author=self.admin,
            author_display_name="Flora",
        )
        self.client.force_login(self.admin)
        response = self.client.post(reverse("archive_enquiry", args=(self.store.id,)))
        self.assertRedirects(response, reverse("enquiry_list"))
        self.store.refresh_from_db()
        self.assertTrue(self.store.archived)
        self.assertIsNotNone(self.store.archived_at)
        self.assertTrue(Note.objects.filter(enquiry=self.store, body="Keep this note").exists())
