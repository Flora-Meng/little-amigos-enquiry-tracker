from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("party_summaries", "0010_partysummary_rsvp_information_partyintakelink")]

    operations = [
        migrations.AddField(
            model_name="partysummary",
            name="confirmed",
            field=models.BooleanField(default=False),
        ),
    ]
