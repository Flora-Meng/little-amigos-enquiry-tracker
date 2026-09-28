from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("party_summaries", "0003_customer_menu_link")]
    operations = [
        migrations.AddField(
            model_name="partymenuitem",
            name="notes",
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
