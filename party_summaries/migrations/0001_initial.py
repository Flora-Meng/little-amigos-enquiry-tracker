import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("accounts", "0002_seed_initial_accounts"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="PartySummary",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("party_date", models.DateField()),
                ("party_time", models.CharField(max_length=80)),
                ("owner_name", models.CharField(max_length=200)),
                ("owner_number", models.CharField(max_length=50)),
                ("food_ready", models.CharField(blank=True, max_length=80)),
                ("room_type", models.CharField(choices=[("single", "Single"), ("double", "Double"), ("triple", "Triple"), ("private", "Private"), ("small_gathering", "Small gathering")], max_length=30)),
                ("kids_count", models.PositiveSmallIntegerField(default=0)),
                ("adults_count", models.PositiveSmallIntegerField(default=0)),
                ("deposit_method", models.CharField(blank=True, max_length=100)),
                ("kids_name", models.CharField(blank=True, max_length=250)),
                ("gender", models.CharField(blank=True, choices=[("girl", "Girl"), ("boy", "Boy"), ("other", "Other")], max_length=20)),
                ("age", models.CharField(blank=True, max_length=40)),
                ("theme", models.CharField(blank=True, max_length=200)),
                ("balloon_color", models.CharField(blank=True, max_length=200)),
                ("special_note", models.TextField(blank=True)),
                ("deposit_amount", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("package_name", models.CharField(choices=[("single_weekday", "Single Weekday $799"), ("single_weekend", "Single Weekend $999"), ("double_weekday", "Double Weekday $1280"), ("double_weekend", "Double Weekend $1580"), ("triple_weekday", "Triple Weekday $2150"), ("triple_weekend", "Triple Weekend $2550"), ("private_weekday", "Private Weekday $3150"), ("private_weekend", "Private Weekend $3550"), ("custom", "Custom / small gathering")], max_length=30)),
                ("package_amount", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("other_charges", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_party_summaries", to=settings.AUTH_USER_MODEL)),
                ("location", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="party_summaries", to="accounts.location")),
            ],
            options={"db_table": "party_summaries", "ordering": ("party_date", "party_time")},
        ),
        migrations.CreateModel(
            name="PartyMenuItem",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("category", models.CharField(choices=[("adult", "Adult menu"), ("kids", "Kids menu"), ("extra", "Extra food")], max_length=10)),
                ("quantity", models.CharField(blank=True, max_length=40)),
                ("item", models.CharField(max_length=250)),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("position", models.PositiveSmallIntegerField(default=0)),
                ("summary", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="menu_items", to="party_summaries.partysummary")),
            ],
            options={"db_table": "party_menu_items", "ordering": ("category", "position", "id")},
        ),
        migrations.AddIndex(model_name="partysummary", index=models.Index(fields=["location", "party_date"], name="party_summa_locatio_ab8b4b_idx")),
        migrations.AddIndex(model_name="partysummary", index=models.Index(fields=["owner_name"], name="party_summa_owner_n_275a60_idx")),
        migrations.AddIndex(model_name="partysummary", index=models.Index(fields=["owner_number"], name="party_summa_owner_n_e3aeab_idx")),
    ]
