from django.db import migrations, models


def preserve_existing_canberra_single_as_voucher(apps, schema_editor):
    PartySummary = apps.get_model("party_summaries", "PartySummary")
    PartySummary.objects.filter(
        location__code="canberra",
        room_type="single",
    ).update(room_type="single_voucher")


def restore_canberra_single(apps, schema_editor):
    PartySummary = apps.get_model("party_summaries", "PartySummary")
    PartySummary.objects.filter(
        location__code="canberra",
        room_type="single_voucher",
    ).update(room_type="single")


class Migration(migrations.Migration):

    dependencies = [("party_summaries", "0011_partysummary_confirmed")]

    operations = [
        migrations.AlterField(
            model_name="partysummary",
            name="room_type",
            field=models.CharField(
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
        migrations.RunPython(
            preserve_existing_canberra_single_as_voucher,
            restore_canberra_single,
        ),
    ]
