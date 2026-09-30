from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('party_summaries', '0007_alter_partysummary_room_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='partysummary',
            name='voucher_menu_notes',
            field=models.TextField(blank=True),
        ),
    ]
