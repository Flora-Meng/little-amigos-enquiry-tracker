from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_southlandshowcasethemephoto_source_summary"),
    ]

    operations = [
        migrations.AddField(
            model_name="southlandshowcaseinvite",
            name="choices_submitted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="southlandshowcaseinvite",
            name="selected_addons",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="southlandshowcaseinvite",
            name="selected_package",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="southlandshowcaseinvite",
            name="selected_theme",
            field=models.CharField(blank=True, max_length=160),
        ),
    ]
