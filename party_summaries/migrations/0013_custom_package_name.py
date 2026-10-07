from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("party_summaries", "0012_add_canberra_single_voucher_room_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="partysummary",
            name="custom_package_name",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name="partysummary",
            name="package_name",
            field=models.CharField(
                choices=[
                    ("classic_weekday", "Classic Weekday"),
                    ("single_weekday", "Single Weekday"),
                    ("single_weekend", "Single Weekend"),
                    ("double_lite_weekday", "Double Lite Weekday"),
                    ("double_lite_weekend", "Double Lite Weekend"),
                    ("double_weekday", "Double Weekday"),
                    ("double_weekend", "Double Weekend"),
                    ("triple_weekday", "Triple Weekday"),
                    ("triple_weekend", "Triple Weekend"),
                    ("private_weekday", "Private Weekday"),
                    ("private_weekend", "Private Weekend"),
                    ("private_weekday_2hour", "Private Weekday 2 hour"),
                    ("private_weekend_2hour", "Private Weekend 2 hour"),
                    ("private_weekday_3hour", "Private Weekday 3 hour"),
                    ("private_weekend_3hour", "Private Weekend 3 hour"),
                    ("custom", "Custom"),
                ],
                max_length=30,
            ),
        ),
    ]
