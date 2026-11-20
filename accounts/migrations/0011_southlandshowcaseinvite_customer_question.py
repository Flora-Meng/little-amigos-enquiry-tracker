from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_themelibraryphoto"),
    ]

    operations = [
        migrations.AddField(
            model_name="southlandshowcaseinvite",
            name="customer_question",
            field=models.TextField(blank=True),
        ),
    ]
