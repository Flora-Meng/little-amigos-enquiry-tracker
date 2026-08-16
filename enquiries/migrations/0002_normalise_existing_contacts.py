from django.db import migrations


def normalise_email(value):
    return (value or "").strip().lower()


def normalise_phone(value):
    digits = "".join(character for character in (value or "") if character.isdigit())
    if digits.startswith("0061"):
        digits = digits[2:]
    if digits.startswith("61") and len(digits) == 11:
        digits = "0" + digits[2:]
    return digits


def update_contacts(apps, schema_editor):
    Enquiry = apps.get_model("enquiries", "Enquiry")
    for enquiry in Enquiry.objects.all().iterator():
        enquiry.normalised_email = normalise_email(enquiry.email)
        enquiry.normalised_phone = normalise_phone(enquiry.phone)
        enquiry.save(update_fields=("normalised_email", "normalised_phone"))


class Migration(migrations.Migration):
    dependencies = [("enquiries", "0001_initial")]
    operations = [migrations.RunPython(update_contacts, migrations.RunPython.noop)]
