from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0011_southlandshowcaseinvite_customer_question"),
    ]

    operations = [
        migrations.AddField(
            model_name="southlandshowcaseinvite",
            name="question_resolved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
