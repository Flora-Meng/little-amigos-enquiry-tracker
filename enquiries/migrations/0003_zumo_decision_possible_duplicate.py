from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("enquiries", "0002_normalise_existing_contacts")]
    operations = [
        migrations.AddField(
            model_name="zumoimportdecision",
            name="possible_duplicate",
            field=models.BooleanField(default=False),
        )
    ]
