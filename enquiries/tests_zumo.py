import json

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from .models import Enquiry, ExtensionToken, ZumoImportDecision
from .routing import normalise_postcode, route_postcode


class ZumoImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.get(email="flora@littleamigos.au")
        cls.staff = User.objects.get(email="southland@littleamigos.com")
        cls.extension_token, cls.raw_token = ExtensionToken.issue(
            user=cls.admin, name="Test Chrome"
        )
        cls.existing = Enquiry.objects.create(
            name="Existing Zumo Match",
            phone="0412 000 999",
            location=cls.staff.location,
            source=Enquiry.Source.STORE,
            status=Enquiry.Status.NEW,
            submitted_by=cls.staff,
        )

    def post_json(self, name, payload, *, client=None):
        return (client or self.client).post(
            reverse(name),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.raw_token}",
        )

    def import_payload(self, conversation_id="conv-001", **changes):
        payload = {
            "conversation_id": conversation_id,
            "conversation_url": f"https://app.zumocrm.com/conversations/{conversation_id}",
            "name": "Eli Enaz",
            "postcode": "3192",
            "party_date": "2027-02-20",
            "email": "eli@example.com",
            "phone": "0450 101 795",
            "original_message": "First name: Eli\nLast name: Enaz",
        }
        payload.update(changes)
        return payload

    def test_postcode_routing_rules(self):
        self.assertEqual(normalise_postcode(" 3 192 "), "3192")
        self.assertEqual(route_postcode("3192"), "southland")
        self.assertEqual(route_postcode("2601"), "canberra")
        self.assertEqual(route_postcode("2912"), "canberra")
        self.assertIsNone(route_postcode("2000"))

    def test_api_requires_admin_and_page_is_admin_only(self):
        anonymous = self.client.get(reverse("zumo_review_status", args=("unknown",)))
        self.assertEqual(anonymous.status_code, 401)
        self.client.force_login(self.staff)
        staff_api = self.client.get(reverse("zumo_review_status", args=("unknown",)))
        staff_page = self.client.get(reverse("zumo_imports"))
        self.assertEqual(staff_api.status_code, 403)
        self.assertEqual(staff_page.status_code, 403)

    def test_review_status_moves_from_not_reviewed_to_ignored(self):
        self.client.force_login(self.admin)
        status_url = reverse("zumo_review_status", args=("conv-ignore",))
        self.assertEqual(self.client.get(status_url).json()["status"], "not_reviewed")
        ignored = self.post_json(
            "zumo_ignore",
            {
                "conversation_id": "conv-ignore",
                "conversation_url": "https://app.zumocrm.com/conversations/conv-ignore",
                "postcode": "2000",
                "original_message": "Not in service area",
            },
        )
        self.assertEqual(ignored.status_code, 201)
        self.assertEqual(self.client.get(status_url).json()["status"], "ignored")
        repeated = self.post_json(
            "zumo_ignore",
            {
                "conversation_id": "conv-ignore",
                "conversation_url": "https://app.zumocrm.com/conversations/conv-ignore",
            },
        )
        self.assertEqual(repeated.status_code, 409)

    def test_import_routes_southland_and_returns_linked_enquiry(self):
        self.client.force_login(self.admin)
        response = self.post_json("zumo_import", self.import_payload())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["assigned_location"], "southland")
        enquiry = Enquiry.objects.get(zumo_conversation_id="conv-001")
        self.assertEqual(enquiry.location.code, "southland")
        self.assertEqual(enquiry.source, Enquiry.Source.ONLINE)
        self.assertEqual(enquiry.status, Enquiry.Status.NEW)
        status = self.client.get(reverse("zumo_review_status", args=("conv-001",))).json()
        self.assertEqual(status["status"], "imported")
        self.assertEqual(status["enquiry_id"], str(enquiry.id))
        self.assertIn(str(enquiry.id), status["enquiry_url"])

    def test_canberra_routing_supports_26_and_29_prefixes(self):
        self.client.force_login(self.admin)
        for index, postcode in enumerate(("2601", "2912"), start=1):
            with self.subTest(postcode=postcode):
                response = self.post_json(
                    "zumo_import",
                    self.import_payload(
                        f"conv-canberra-{index}",
                        postcode=postcode,
                        email=f"canberra{index}@example.com",
                        phone=f"0400 000 00{index}",
                    ),
                )
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.json()["assigned_location"], "canberra")

    def test_out_of_area_requires_explicit_override(self):
        self.client.force_login(self.admin)
        payload = self.import_payload("conv-outside", postcode="2000")
        blocked = self.post_json("zumo_import", payload)
        self.assertEqual(blocked.status_code, 422)
        self.assertEqual(blocked.json()["error"], "out_of_area")
        self.assertFalse(Enquiry.objects.filter(zumo_conversation_id="conv-outside").exists())

        payload["override_location"] = "canberra"
        imported = self.post_json("zumo_import", payload)
        self.assertEqual(imported.status_code, 201)
        decision = ZumoImportDecision.objects.get(zumo_conversation_id="conv-outside")
        self.assertIsNone(decision.detected_location)
        self.assertEqual(decision.linked_enquiry.location.code, "canberra")

    def test_duplicate_import_warns_then_allows_confirmed_creation(self):
        self.client.force_login(self.admin)
        payload = self.import_payload("conv-duplicate", phone="+61 412 000 999")
        warning = self.post_json("zumo_import", payload)
        self.assertEqual(warning.status_code, 409)
        self.assertEqual(warning.json()["error"], "possible_duplicate")
        self.assertEqual(warning.json()["matches"][0]["name"], "Existing Zumo Match")
        self.assertFalse(Enquiry.objects.filter(zumo_conversation_id="conv-duplicate").exists())

        payload["confirm_duplicate"] = True
        imported = self.post_json("zumo_import", payload)
        self.assertEqual(imported.status_code, 201)
        decision = ZumoImportDecision.objects.get(zumo_conversation_id="conv-duplicate")
        self.assertTrue(decision.possible_duplicate)

    def test_imported_conversation_cannot_silently_create_twice(self):
        self.client.force_login(self.admin)
        payload = self.import_payload("conv-once")
        self.assertEqual(self.post_json("zumo_import", payload).status_code, 201)
        self.assertEqual(self.post_json("zumo_import", payload).status_code, 409)
        self.assertEqual(Enquiry.objects.filter(zumo_conversation_id="conv-once").count(), 1)

    def test_admin_history_page_shows_imported_ignored_duplicate_and_out_of_area(self):
        self.client.force_login(self.admin)
        self.post_json("zumo_import", self.import_payload("conv-page"))
        self.post_json(
            "zumo_ignore",
            {
                "conversation_id": "conv-page-ignore",
                "conversation_url": "https://app.zumocrm.com/conversations/conv-page-ignore",
                "postcode": "2000",
            },
        )
        response = self.client.get(reverse("zumo_imports"))
        self.assertContains(response, "conv-page")
        self.assertContains(response, "conv-page-ignore")
        self.assertContains(response, "Out of area")
        self.assertEqual(response.context["imported_count"], 1)
        self.assertEqual(response.context["ignored_count"], 1)

    def test_invalid_json_and_invalid_party_date_are_rejected(self):
        self.client.force_login(self.admin)
        invalid_json = self.client.post(
            reverse("zumo_import"),
            data="{",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.raw_token}",
        )
        self.assertEqual(invalid_json.status_code, 400)
        invalid_date = self.post_json(
            "zumo_import", self.import_payload("conv-bad-date", party_date="20 February")
        )
        self.assertEqual(invalid_date.status_code, 422)
        self.assertEqual(invalid_date.json()["error"], "invalid_party_date")

    def test_write_api_rejects_session_only_but_accepts_token_with_csrf_checks(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.admin)
        session_only = csrf_client.post(
            reverse("zumo_import"),
            data=json.dumps(self.import_payload("conv-session-only")),
            content_type="application/json",
        )
        self.assertEqual(session_only.status_code, 401)
        token_request = self.post_json(
            "zumo_import",
            self.import_payload("conv-token-csrf"),
            client=csrf_client,
        )
        self.assertEqual(token_request.status_code, 201)

    def test_revoked_token_is_rejected(self):
        self.extension_token.revoked_at = timezone.now()
        self.extension_token.save(update_fields=("revoked_at",))
        response = self.post_json("zumo_import", self.import_payload("conv-revoked"))
        self.assertEqual(response.status_code, 401)

    def test_review_again_only_reopens_ignored_conversation(self):
        self.client.force_login(self.admin)
        self.post_json(
            "zumo_ignore",
            {
                "conversation_id": "conv-review-again",
                "conversation_url": "https://app.zumocrm.com/conversations/conv-review-again",
                "postcode": "3192",
            },
        )
        response = self.client.post(
            reverse("zumo_review_again", args=("conv-review-again",)),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.raw_token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            ZumoImportDecision.objects.filter(
                zumo_conversation_id="conv-review-again"
            ).exists()
        )

    def test_token_settings_shows_plaintext_once_and_stores_only_hash(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("extension_token_settings"),
            {"action": "create", "name": "Flora laptop"},
        )
        self.assertEqual(response.status_code, 200)
        raw = response.context["raw_token"]
        self.assertTrue(raw.startswith("laet_"))
        created = ExtensionToken.objects.get(name="Flora laptop")
        self.assertNotEqual(created.token_hash, raw)
        later = self.client.get(reverse("extension_token_settings"))
        self.assertNotContains(later, raw)
