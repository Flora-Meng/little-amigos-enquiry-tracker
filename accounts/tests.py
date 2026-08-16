from django.contrib.auth import authenticate, get_user_model
from django.test import TestCase

from .models import Location


class InitialAccountsTests(TestCase):
    def test_three_initial_accounts_have_expected_roles_and_locations(self):
        User = get_user_model()
        flora = User.objects.get(email="flora@littleamigos.au")
        kiva = User.objects.get(email="southland@littleamigos.com")
        emma = User.objects.get(email="canberra@littleamigos.com")

        self.assertEqual(User.objects.count(), 3)
        self.assertEqual(Location.objects.count(), 2)
        self.assertEqual(flora.role, User.Role.ADMIN)
        self.assertIsNone(flora.location)
        self.assertTrue(flora.is_superuser)
        self.assertEqual(kiva.location.code, Location.Code.SOUTHLAND)
        self.assertEqual(emma.location.code, Location.Code.CANBERRA)

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
