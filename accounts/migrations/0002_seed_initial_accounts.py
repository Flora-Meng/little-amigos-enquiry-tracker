from django.contrib.auth.hashers import make_password
from django.db import migrations


def seed_initial_accounts(apps, schema_editor):
    Location = apps.get_model("accounts", "Location")
    User = apps.get_model("accounts", "User")

    southland, _ = Location.objects.update_or_create(
        code="southland",
        defaults={"name": "Little Amigos Southland", "timezone": "Australia/Sydney"},
    )
    canberra, _ = Location.objects.update_or_create(
        code="canberra",
        defaults={"name": "Little Amigos Canberra", "timezone": "Australia/Sydney"},
    )

    profiles = (
        {
            "email": "flora@littleamigos.au",
            "display_name": "Flora",
            "role": "admin",
            "location": None,
            "is_staff": True,
            "is_superuser": True,
        },
        {
            "email": "southland@littleamigos.com",
            "display_name": "Kiva",
            "role": "staff",
            "location": southland,
            "is_staff": False,
            "is_superuser": False,
        },
        {
            "email": "canberra@littleamigos.com",
            "display_name": "Emma",
            "role": "staff",
            "location": canberra,
            "is_staff": False,
            "is_superuser": False,
        },
    )

    for profile in profiles:
        email = profile.pop("email")
        user, created = User.objects.get_or_create(email=email, defaults=profile)
        if created:
            user.password = make_password(None)
            user.password_reset_required = True
            user.save(update_fields=("password", "password_reset_required"))


def remove_initial_accounts(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(
        email__in=(
            "flora@littleamigos.au",
            "southland@littleamigos.com",
            "canberra@littleamigos.com",
        )
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]
    operations = [migrations.RunPython(seed_initial_accounts, remove_initial_accounts)]
