from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import Location


class InitialAccountsTests(TestCase):
    def test_three_initial_accounts_have_expected_roles_and_locations(self):
        User = get_user_model()
        flora = User.objects.get(email="flora@littleamigos.au")
        kiva = User.objects.get(email="southland@littleamigos.com")
        canberra = User.objects.get(email="canberra@littleamigos.com")

        self.assertEqual(User.objects.count(), 3)
        self.assertEqual(Location.objects.count(), 2)
        self.assertEqual(flora.role, User.Role.ADMIN)
        self.assertIsNone(flora.location)
        self.assertTrue(flora.is_superuser)
        self.assertEqual(kiva.location.code, Location.Code.SOUTHLAND)
        self.assertEqual(canberra.location.code, Location.Code.CANBERRA)
        self.assertEqual(kiva.display_name, "Kiva")
        self.assertEqual(canberra.display_name, "Little Amigos Canberra")

    def test_seeded_accounts_do_not_have_a_source_controlled_password(self):
        User = get_user_model()
        for user in User.objects.all():
            self.assertFalse(user.has_usable_password())
            self.assertTrue(user.password_reset_required)

    def test_email_and_argon2_password_authentication(self):
        User = get_user_model()
        flora = User.objects.get(email="flora@littleamigos.au")
        flora.set_password("Test-only strong password 47!")
        flora.password_reset_required = False
        flora.save()

        authenticated = authenticate(
            email="flora@littleamigos.au",
            password="Test-only strong password 47!",
        )

        self.assertEqual(authenticated, flora)
        self.assertTrue(flora.password.startswith("argon2$"))


class TeamAccountSetupTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.get(email="flora@littleamigos.au")
        self.southland = User.objects.get(email="southland@littleamigos.com")
        self.canberra = User.objects.get(email="canberra@littleamigos.com")

    def _setup_url(self, user):
        return reverse(
            "staff_password_setup",
            kwargs={
                "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
                "token": default_token_generator.make_token(user),
            },
        )

    def test_only_admin_can_open_team_accounts(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("team_accounts"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kiva")
        self.assertContains(response, "Little Amigos Canberra")
        self.assertContains(response, "Southland only")
        self.assertContains(response, "Canberra only")

        self.client.force_login(self.southland)
        self.assertEqual(self.client.get(reverse("team_accounts")).status_code, 403)

    def test_private_setup_link_sets_password_and_cannot_be_reused(self):
        setup_url = self._setup_url(self.canberra)
        response = self.client.get(setup_url)
        self.assertEqual(response.status_code, 302)

        response = self.client.get(response.url)
        self.assertContains(response, "Set your password")
        saved = self.client.post(
            response.request["PATH_INFO"],
            {
                "new_password1": "Canberra private password 47!",
                "new_password2": "Canberra private password 47!",
            },
        )
        self.assertRedirects(saved, reverse("staff_password_setup_complete"))
        self.canberra.refresh_from_db()
        self.assertTrue(self.canberra.check_password("Canberra private password 47!"))
        self.assertFalse(self.canberra.password_reset_required)
        self.assertFalse(default_token_generator.check_token(
            self.canberra,
            setup_url.rsplit("/", 2)[-2],
        ))
