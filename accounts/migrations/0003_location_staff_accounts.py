from django.contrib.auth.hashers import make_password
from django.db import migrations


def configure_location_accounts(apps, schema_editor):
    Location = apps.get_model("accounts", "Location")
    User = apps.get_model("accounts", "User")

    account_profiles = (
        ("southland", "southland@littleamigos.com", "Kiva"),
        ("canberra", "canberra@littleamigos.com", "Little Amigos Canberra"),
    )
    for location_code, email, display_name in account_profiles:
        location = Location.objects.get(code=location_code)
        user, created = User.objects.update_or_create(
            email=email,
            defaults={
                "display_name": display_name,
                "role": "staff",
                "location": location,
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
            },
        )
        if created:
            user.password = make_password(None)
            user.password_reset_required = True
            user.save(update_fields=("password", "password_reset_required"))


def restore_canberra_name(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(email="canberra@littleamigos.com").update(display_name="Emma")


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_seed_initial_accounts")]
    operations = [migrations.RunPython(configure_location_accounts, restore_canberra_name)]
