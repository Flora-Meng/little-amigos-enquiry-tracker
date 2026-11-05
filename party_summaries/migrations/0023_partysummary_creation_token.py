from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("party_summaries", "0022_partysummary_lark_sync_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="partysummary",
            name="creation_token",
            field=models.UUIDField(blank=True, editable=False, null=True, unique=True),
        ),
    ]
