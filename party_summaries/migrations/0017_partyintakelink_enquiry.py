from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("enquiries", "0004_extension_token"),
        ("party_summaries", "0016_fix_extra_food_line_totals"),
    ]

    operations = [
        migrations.AddField(
            model_name="partyintakelink",
            name="enquiry",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="party_intake_link",
                to="enquiries.enquiry",
            ),
        ),
    ]
