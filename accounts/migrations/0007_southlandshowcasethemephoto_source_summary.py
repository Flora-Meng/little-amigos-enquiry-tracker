import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_southlandshowcaseinvite"),
        ("party_summaries", "0021_alter_partysummary_gender_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="southlandshowcasethemephoto",
            name="source_summary",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="southland_showcase_photos",
                to="party_summaries.partysummary",
            ),
        ),
        migrations.AddConstraint(
            model_name="southlandshowcasethemephoto",
            constraint=models.UniqueConstraint(
                condition=models.Q(("source_summary__isnull", False)),
                fields=("theme", "source_summary"),
                name="unique_summary_photo_per_southland_theme",
            ),
        ),
    ]
