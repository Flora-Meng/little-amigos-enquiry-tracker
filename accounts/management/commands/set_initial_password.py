from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Interactively set an initial password without exposing it in source or shell history."

    def add_arguments(self, parser):
        parser.add_argument("email")

    def handle(self, *args, **options):
        User = get_user_model()
        email = options["email"].strip().lower()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist as exc:
            raise CommandError(f"No account exists for {email}") from exc

        first = getpass("New password: ")
        second = getpass("Confirm password: ")
        if first != second:
            raise CommandError("Passwords do not match")
        try:
            validate_password(first, user=user)
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages)) from exc

        user.set_password(first)
        user.password_reset_required = False
        user.save(update_fields=("password", "password_reset_required", "updated_at"))
        self.stdout.write(self.style.SUCCESS(f"Initial password set for {email}"))
