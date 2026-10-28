from django.test import TestCase
from django.urls import reverse


class HealthCheckTests(TestCase):
    def test_health_check_reports_ok_without_authentication(self):
        response = self.client.get(reverse("health_check"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class PartyPlannerDemoTests(TestCase):
    def test_demo_is_public_and_renders_the_guided_flow(self):
        response = self.client.get(reverse("party_planner_demo"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Find your party")
        self.assertContains(response, "Two party options suit your enquiry")
        self.assertContains(response, "Would you like any extra services?")
        self.assertContains(response, "Lock me in")
        self.assertContains(response, "deposit invoice")
