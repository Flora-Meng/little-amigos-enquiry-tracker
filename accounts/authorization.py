from enum import StrEnum

from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet

from .models import User


class Action(StrEnum):
    VIEW_ENQUIRY = "view_enquiry"
    CREATE_STORE_ENQUIRY = "create_store_enquiry"
    EDIT_CUSTOMER = "edit_customer"
    CHANGE_STATUS = "change_status"
    CHANGE_BOOKING_AMOUNT = "change_booking_amount"
    CHANGE_CLOSED_REASON = "change_closed_reason"
    UPDATE_FOLLOW_UP = "update_follow_up"
    ADD_NOTE = "add_note"
    ARCHIVE_ENQUIRY = "archive_enquiry"
    ACCESS_ZUMO = "access_zumo"
    RESET_EMPLOYEE_PASSWORD = "reset_employee_password"


ADMIN_ONLY_ENQUIRY_ACTIONS = frozenset(
    {
        Action.EDIT_CUSTOMER,
        Action.CHANGE_STATUS,
        Action.CHANGE_BOOKING_AMOUNT,
        Action.CHANGE_CLOSED_REASON,
        Action.UPDATE_FOLLOW_UP,
        Action.ARCHIVE_ENQUIRY,
    }
)


def is_authenticated_active(user) -> bool:
    return bool(getattr(user, "is_authenticated", False) and user.is_active)


def can_view_enquiry(user, enquiry) -> bool:
    if not is_authenticated_active(user):
        return False
    if user.role == User.Role.ADMIN:
        return True
    return bool(
        user.role == User.Role.STAFF
        and user.location_id is not None
        and enquiry.source == "store"
        and enquiry.location_id == user.location_id
    )


def can_perform(user, action: Action, *, enquiry=None, target_user=None) -> bool:
    if not is_authenticated_active(user):
        return False

    if action == Action.CREATE_STORE_ENQUIRY:
        return user.role in {User.Role.ADMIN, User.Role.STAFF}

    if action == Action.ACCESS_ZUMO:
        return user.role == User.Role.ADMIN

    if action == Action.RESET_EMPLOYEE_PASSWORD:
        return bool(
            user.role == User.Role.ADMIN
            and target_user is not None
            and target_user.role == User.Role.STAFF
        )

    if enquiry is None or not can_view_enquiry(user, enquiry):
        return False

    if action in {Action.VIEW_ENQUIRY, Action.ADD_NOTE}:
        return True

    if action in ADMIN_ONLY_ENQUIRY_ACTIONS:
        return user.role == User.Role.ADMIN

    return False


def require_permission(user, action: Action, *, enquiry=None, target_user=None) -> None:
    """Raise a server-side 403 when an action is not authorised."""
    if not can_perform(user, action, enquiry=enquiry, target_user=target_user):
        raise PermissionDenied(f"Not authorised to perform {action.value}")


def enquiries_visible_to(user, queryset: QuerySet) -> QuerySet:
    """Return only rows the user may receive; never filter sensitive rows in-browser."""
    if not is_authenticated_active(user):
        return queryset.none()
    if user.role == User.Role.ADMIN:
        return queryset.all()
    if user.role == User.Role.STAFF and user.location_id is not None:
        return queryset.filter(source="store", location_id=user.location_id)
    return queryset.none()
