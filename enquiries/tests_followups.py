from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from .models import Enquiry
from .services import due_today, overdue, schedule_next_follow_up, two_calendar_days_from


class FollowUpServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.get(email="flora@littleamigos.au")
        cls.staff = User.objects.get(email="southland@littleamigos.com")
        cls.today = timezone.localdate()

        def create(name, due, status=Enquiry.Status.FOLLOW_UP, archived=False, amount=None):
            return Enquiry.objects.create(
                name=name,
                email=f"{name.lower().replace(' ', '.')}@example.com",
                location=cls.staff.location,
                source=Enquiry.Source.STORE,
                status=status,
                follow_up_due_date=due,
                archived=archived,
                archived_at=timezone.now() if archived else None,
                booking_amount_aud=amount,
                closed_reason=(
                    Enquiry.ClosedReason.PRICE if status == Enquiry.Status.CLOSED else ""
                ),
                submitted_by=cls.staff,
            )

        cls.due = create("Due Today", cls.today)
        cls.late = create("Overdue Item", cls.today - timedelta(days=1))
        cls.future = create("Future Item", cls.today + timedelta(days=1))
        cls.closed = create("Closed Item", cls.today - timedelta(days=3), Enquiry.Status.CLOSED)
        cls.booked = create(
            "Booked Item",
            cls.today,
            Enquiry.Status.BOOKED,
            amount=Decimal("500.00"),
        )
        cls.archived = create("Archived Item", cls.today, archived=True)

    def test_two_calendar_day_calculation_is_exact(self):
        self.assertEqual(two_calendar_days_from(date(2026, 12, 31)), date(2027, 1, 2))

    def test_due_and_overdue_queries_exclude_terminal_and_archived_records(self):
        all_enquiries = Enquiry.objects.all()
        self.assertEqual(list(due_today(all_enquiries, today=self.today)), [self.due])
        self.assertEqual(list(overdue(all_enquiries, today=self.today)), [self.late])

    def test_admin_dashboard_counts_match_follow_up_services(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard"))
        card_values = {label: value for label, value, style in response.context["cards"]}
        self.assertEqual(card_values["Follow-ups due today"], 1)
        self.assertEqual(card_values["Overdue follow-ups"], 1)

    def test_admin_can_schedule_next_follow_up_for_open_enquiry(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("reschedule_follow_up", args=(self.late.id,)))
        self.assertRedirects(response, reverse("enquiry_detail", args=(self.late.id,)))
        self.late.refresh_from_db()
        self.assertEqual(self.late.follow_up_due_date, self.today + timedelta(days=2))

    def test_staff_cannot_reschedule_follow_up(self):
        self.client.force_login(self.staff)
        original = self.due.follow_up_due_date
        response = self.client.post(reverse("reschedule_follow_up", args=(self.due.id,)))
        self.assertEqual(response.status_code, 403)
        self.due.refresh_from_db()
        self.assertEqual(self.due.follow_up_due_date, original)

    def test_terminal_enquiry_cannot_be_rescheduled(self):
        with self.assertRaisesMessage(ValueError, "cannot have an active follow-up"):
            schedule_next_follow_up(self.closed, today=self.today)
        self.client.force_login(self.admin)
        response = self.client.post(reverse("reschedule_follow_up", args=(self.closed.id,)))
        self.assertRedirects(response, reverse("enquiry_detail", args=(self.closed.id,)))
        self.closed.refresh_from_db()
        self.assertEqual(self.closed.follow_up_due_date, self.today - timedelta(days=3))
