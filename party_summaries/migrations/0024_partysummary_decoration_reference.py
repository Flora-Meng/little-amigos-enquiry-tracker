from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("party_summaries", "0023_partysummary_creation_token"),
    ]

    operations = [
        migrations.AddField(
            model_name="partysummary",
            name="decoration_reference",
            field=models.BinaryField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="partysummary",
            name="decoration_reference_content_type",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="partysummary",
            name="decoration_reference_name",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
