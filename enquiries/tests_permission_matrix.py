import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Enquiry, Note


class CompletePermissionMatrixTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.get(email="flora@littleamigos.au")
        cls.southland = User.objects.get(email="southland@littleamigos.com")
        cls.canberra = User.objects.get(email="canberra@littleamigos.com")
        for user in (cls.admin, cls.southland, cls.canberra):
            user.set_password("Test-only strong password 47!")
            user.save()

        cls.southland_store = Enquiry.objects.create(
            name="Southland Permission Record",
            phone="0400 100 100",
            location=cls.southland.location,
            source=Enquiry.Source.STORE,
            status=Enquiry.Status.NEW,
            submitted_by=cls.southland,
        )
        cls.canberra_store = Enquiry.objects.create(
            name="Canberra Permission Record",
            email="canberra.permission@example.com",
            location=cls.canberra.location,
            source=Enquiry.Source.STORE,
            status=Enquiry.Status.NEW,
            submitted_by=cls.canberra,
        )
        cls.online = Enquiry.objects.create(
            name="Admin-only Online Record",
            email="online.permission@example.com",
            location=cls.southland.location,
            source=Enquiry.Source.ONLINE,
            status=Enquiry.Status.NEW,
            submitted_by=cls.admin,
            zumo_conversation_id="permission-matrix-online",
        )

    def update_payload(self, enquiry, **changes):
        payload = {
            "name": enquiry.name,
            "phone": enquiry.phone,
            "email": enquiry.email,
            "postcode": enquiry.postcode,
            "party_date": "",
            "location": str(enquiry.location_id),
            "status": enquiry.status,
            "follow_up_due_date": "",
            "booking_amount_aud": "",
            "closed_reason": "",
            "closed_reason_details": "",
        }
        payload.update(changes)
        return payload

    def test_anonymous_users_are_redirected_from_all_webapp_pages(self):
        protected = (
            reverse("dashboard"),
            reverse("enquiry_list"),
            reverse("new_store_enquiry"),
            reverse("enquiry_detail", args=(self.southland_store.id,)),
            reverse("zumo_imports"),
            reverse("extension_token_settings"),
        )
        for url in protected:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("login"), response.url)

    def test_admin_receives_all_locations_and_sources(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("enquiry_list"))
        for name in (
            self.southland_store.name,
            self.canberra_store.name,
            self.online.name,
        ):
            self.assertContains(response, name)
        for enquiry in (
            self.southland_store,
            self.canberra_store,
            self.online,
        ):
            detail = self.client.get(reverse("enquiry_detail", args=(enquiry.id,)))
            self.assertEqual(detail.status_code, 200)

    def test_each_staff_list_only_contains_own_location_rows(self):
        cases = (
            (self.southland, self.southland_store, self.canberra_store),
            (self.canberra, self.canberra_store, self.southland_store),
        )
        for user, allowed, other_store in cases:
            with self.subTest(user=user.email):
                self.client.force_login(user)
                response = self.client.get(reverse("enquiry_list"), {"archived": "all"})
                self.assertContains(response, allowed.name)
                self.assertNotContains(response, other_store.name)
                if user == self.southland:
                    self.assertContains(response, self.online.name)
                else:
                    self.assertNotContains(response, self.online.name)

    def test_staff_guessed_urls_return_404_without_revealing_record_existence(self):
        cases = (
            (self.southland, self.canberra_store),
            (self.canberra, self.southland_store),
            (self.canberra, self.online),
        )
        for user, enquiry in cases:
            with self.subTest(user=user.email, enquiry=enquiry.name):
                self.client.force_login(user)
                response = self.client.get(reverse("enquiry_detail", args=(enquiry.id,)))
                self.assertEqual(response.status_code, 404)

    def test_staff_direct_mutation_requests_are_403_and_database_is_unchanged(self):
        self.client.force_login(self.southland)
        enquiry = self.southland_store
        attempts = (
            (
                reverse("update_enquiry", args=(enquiry.id,)),
                self.update_payload(
                    enquiry,
                    name="Tampered customer",
                    status=Enquiry.Status.BOOKED,
                    booking_amount_aud="1.00",
                ),
            ),
            (reverse("archive_enquiry", args=(enquiry.id,)), {}),
            (reverse("reschedule_follow_up", args=(enquiry.id,)), {}),
        )
        for url, payload in attempts:
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, payload).status_code, 403)
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.name, "Southland Permission Record")
        self.assertEqual(enquiry.status, Enquiry.Status.NEW)
        self.assertIsNone(enquiry.booking_amount_aud)
        self.assertIsNone(enquiry.follow_up_due_date)
        self.assertFalse(enquiry.archived)

    def test_staff_can_append_note_only_to_own_location_records(self):
        self.client.force_login(self.southland)
        allowed = self.client.post(
            reverse("add_note", args=(self.southland_store.id,)),
            {"body": "Kiva authorised note"},
        )
        online = self.client.post(
            reverse("add_note", args=(self.online.id,)),
            {"body": "Southland online note"},
        )
        other = self.client.post(
            reverse("add_note", args=(self.canberra_store.id,)),
            {"body": "Canberra leak"},
        )
        self.assertEqual(allowed.status_code, 302)
        self.assertEqual(online.status_code, 302)
        self.assertEqual(other.status_code, 404)
        self.assertTrue(Note.objects.filter(body="Kiva authorised note").exists())
        self.assertTrue(Note.objects.filter(body="Southland online note").exists())
        self.assertFalse(Note.objects.filter(body="Canberra leak").exists())

    def test_staff_creation_ignores_forged_location_source_status_and_amount(self):
        self.client.force_login(self.canberra)
        response = self.client.post(
            reverse("new_store_enquiry"),
            {
                "name": "Forged Canberra Submission",
                "email": "forged@example.com",
                "location": str(self.southland.location_id),
                "source": Enquiry.Source.ONLINE,
                "status": Enquiry.Status.BOOKED,
                "booking_amount_aud": "9999.00",
            },
        )
        self.assertEqual(response.status_code, 302)
        created = Enquiry.objects.get(name="Forged Canberra Submission")
        self.assertEqual(created.location, self.canberra.location)
        self.assertEqual(created.source, Enquiry.Source.STORE)
        self.assertEqual(created.status, Enquiry.Status.NEW)
        self.assertIsNone(created.booking_amount_aud)

    def test_admin_can_create_store_enquiry_for_either_location(self):
        self.client.force_login(self.admin)
        for user, suffix in ((self.southland, "South"), (self.canberra, "Canberra")):
            with self.subTest(location=user.location.code):
                response = self.client.post(
                    reverse("new_store_enquiry"),
                    {
                        "name": f"Admin {suffix} Creation",
                        "email": f"admin.{suffix.lower()}@example.com",
                        "location": str(user.location_id),
                    },
                )
                self.assertEqual(response.status_code, 302)
                created = Enquiry.objects.get(name=f"Admin {suffix} Creation")
                self.assertEqual(created.location, user.location)

    def test_zumo_pages_tokens_and_api_are_admin_only(self):
        for user in (self.southland, self.canberra):
            with self.subTest(user=user.email):
                self.client.force_login(user)
                self.assertEqual(self.client.get(reverse("zumo_imports")).status_code, 403)
                self.assertEqual(
                    self.client.get(reverse("extension_token_settings")).status_code,
                    403,
                )
                status_api = self.client.get(
                    reverse("zumo_review_status", args=("permission-check",))
                )
                self.assertEqual(status_api.status_code, 403)
                write_api = self.client.post(
                    reverse("zumo_import"),
                    data=json.dumps({}),
                    content_type="application/json",
                )
                self.assertEqual(write_api.status_code, 401)

    def test_only_admin_can_access_django_password_reset_surface(self):
        password_url = reverse(
            "admin:auth_user_password_change", args=(self.southland.id,)
        )
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(password_url).status_code, 200)
        self.client.force_login(self.southland)
        staff_response = self.client.get(password_url)
        self.assertEqual(staff_response.status_code, 302)
        self.assertIn("/admin/login/", staff_response.url)

    def test_admin_can_reset_employee_password_but_staff_cannot(self):
        password_url = reverse(
            "admin:auth_user_password_change", args=(self.southland.id,)
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            password_url,
            {
                "password1": "Replacement strong password 83!",
                "password2": "Replacement strong password 83!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.southland.refresh_from_db()
        self.assertTrue(
            self.southland.check_password("Replacement strong password 83!")
        )

    def test_inactive_staff_session_has_no_application_access(self):
        self.southland.is_active = False
        self.southland.save(update_fields=("is_active",))
        self.client.force_login(self.southland)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)
