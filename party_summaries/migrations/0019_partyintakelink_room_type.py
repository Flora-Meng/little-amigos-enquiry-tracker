from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("party_summaries", "0018_partyintakelink_e_invitation_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="partyintakelink",
            name="room_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("single", "Single"),
                    ("single_voucher", "Single (voucher)"),
                    ("double_lite", "Double room Lite"),
                    ("double", "Double"),
                    ("triple", "Triple"),
                    ("private", "Private"),
                    ("private_2hour", "Private 2 hour"),
                    ("private_3hour", "Private 3 hour"),
                    ("small_gathering", "Small gathering"),
                ],
                max_length=30,
            ),
        ),
    ]
