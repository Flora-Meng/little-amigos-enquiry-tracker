import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("enquiries", "0004_extension_token"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EnquiryImage",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("image", models.BinaryField(editable=False)),
                ("file_name", models.CharField(max_length=255)),
                ("content_type", models.CharField(max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("enquiry", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="images", to="enquiries.enquiry")),
                ("uploaded_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="enquiry_images", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "enquiry_images", "ordering": ("created_at",)},
        ),
    ]
