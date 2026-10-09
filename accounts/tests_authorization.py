from types import SimpleNamespace

from django.core.exceptions import PermissionDenied
from django.test import TestCase

from .authorization import Action, can_perform, can_view_enquiry, require_permission
from .models import User


class AuthorisationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.get(email="flora@littleamigos.au")
        cls.southland = User.objects.get(email="southland@littleamigos.com")
        cls.canberra = User.objects.get(email="canberra@littleamigos.com")
        cls.southland_store = SimpleNamespace(
            source="store", location_id=cls.southland.location_id
        )
        cls.canberra_store = SimpleNamespace(
            source="store", location_id=cls.canberra.location_id
        )
        cls.southland_online = SimpleNamespace(
            source="online", location_id=cls.southland.location_id
        )

    def test_admin_can_view_all_enquiry_sources_and_locations(self):
        for enquiry in (
            self.southland_store,
            self.canberra_store,
            self.southland_online,
        ):
            self.assertTrue(can_view_enquiry(self.admin, enquiry))

    def test_staff_only_views_own_location_enquiries(self):
        self.assertTrue(can_view_enquiry(self.southland, self.southland_store))
        self.assertFalse(can_view_enquiry(self.southland, self.canberra_store))
        self.assertTrue(can_view_enquiry(self.southland, self.southland_online))
        self.assertFalse(can_view_enquiry(self.canberra, self.southland_store))

    def test_staff_can_create_store_enquiries_and_add_authorised_notes(self):
        self.assertTrue(can_perform(self.southland, Action.CREATE_STORE_ENQUIRY))
        self.assertTrue(
            can_perform(self.southland, Action.ADD_NOTE, enquiry=self.southland_store)
        )
        self.assertTrue(
            can_perform(self.southland, Action.ADD_NOTE, enquiry=self.southland_online)
        )

    def test_staff_cannot_call_protected_update_actions(self):
        protected = (
            Action.EDIT_CUSTOMER,
            Action.CHANGE_STATUS,
            Action.CHANGE_BOOKING_AMOUNT,
            Action.CHANGE_CLOSED_REASON,
            Action.UPDATE_FOLLOW_UP,
            Action.ARCHIVE_ENQUIRY,
        )
        for action in protected:
            with self.subTest(action=action):
                self.assertFalse(
                    can_perform(self.southland, action, enquiry=self.southland_store)
                )
                with self.assertRaises(PermissionDenied):
                    require_permission(
                        self.southland, action, enquiry=self.southland_store
                    )

    def test_zumo_and_employee_password_reset_are_admin_only(self):
        self.assertTrue(can_perform(self.admin, Action.ACCESS_ZUMO))
        self.assertFalse(can_perform(self.southland, Action.ACCESS_ZUMO))
        self.assertTrue(
            can_perform(
                self.admin,
                Action.RESET_EMPLOYEE_PASSWORD,
                target_user=self.southland,
            )
        )
        self.assertFalse(
            can_perform(
                self.southland,
                Action.RESET_EMPLOYEE_PASSWORD,
                target_user=self.canberra,
            )
        )
        self.assertFalse(
            can_perform(
                self.admin,
                Action.RESET_EMPLOYEE_PASSWORD,
                target_user=self.admin,
            )
        )

    def test_inactive_accounts_have_no_access(self):
        self.southland.is_active = False
        self.assertFalse(can_view_enquiry(self.southland, self.southland_store))
        self.assertFalse(can_perform(self.southland, Action.CREATE_STORE_ENQUIRY))
