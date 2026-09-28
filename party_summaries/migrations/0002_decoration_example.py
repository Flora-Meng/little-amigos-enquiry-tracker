from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("party_summaries", "0001_initial")]
    operations = [
        migrations.AddField(model_name="partysummary", name="decoration_example", field=models.BinaryField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="partysummary", name="decoration_example_content_type", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="partysummary", name="decoration_example_name", field=models.CharField(blank=True, max_length=255)),
    ]
