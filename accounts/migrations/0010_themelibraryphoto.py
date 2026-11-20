import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0009_replace_southland_theme_catalog"),
    ]

    operations = [
        migrations.CreateModel(
            name="ThemeLibraryPhoto",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("theme", models.CharField(max_length=160)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("image_data", models.BinaryField(editable=False)),
                ("image_name", models.CharField(max_length=255)),
                ("image_content_type", models.CharField(max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="theme_library_photos", to="accounts.user")),
                ("location", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="theme_library_photos", to="accounts.location")),
            ],
            options={"ordering": ("-updated_at",)},
        ),
    ]
