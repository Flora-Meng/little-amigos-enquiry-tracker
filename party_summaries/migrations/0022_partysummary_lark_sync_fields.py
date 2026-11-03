from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("party_summaries", "0021_alter_partysummary_gender_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="partysummary",
            name="lark_party_id",
            field=models.CharField(blank=True, editable=False, max_length=100),
        ),
        migrations.AddField(
            model_name="partysummary",
            name="lark_order_record_id",
            field=models.CharField(blank=True, editable=False, max_length=100),
        ),
        migrations.AddField(
            model_name="partysummary",
            name="lark_sync_error",
            field=models.TextField(blank=True, editable=False),
        ),
        migrations.AddField(
            model_name="partysummary",
            name="lark_synced_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
    ]
