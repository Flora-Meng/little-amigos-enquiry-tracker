import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models

from accounts.models import Location


class PartySummary(models.Model):
    class RoomType(models.TextChoices):
        SINGLE = "single", "Single"
        DOUBLE = "double", "Double"
        TRIPLE = "triple", "Triple"
        PRIVATE = "private", "Private"
        SMALL_GATHERING = "small_gathering", "Small gathering"

    class Gender(models.TextChoices):
        GIRL = "girl", "Girl"
        BOY = "boy", "Boy"
        OTHER = "other", "Other"

    class Package(models.TextChoices):
        SINGLE_WEEKDAY = "single_weekday", "Single Weekday $799"
        SINGLE_WEEKEND = "single_weekend", "Single Weekend $999"
        DOUBLE_WEEKDAY = "double_weekday", "Double Weekday $1280"
        DOUBLE_WEEKEND = "double_weekend", "Double Weekend $1580"
        TRIPLE_WEEKDAY = "triple_weekday", "Triple Weekday $2150"
        TRIPLE_WEEKEND = "triple_weekend", "Triple Weekend $2550"
        PRIVATE_WEEKDAY = "private_weekday", "Private Weekday $3150"
        PRIVATE_WEEKEND = "private_weekend", "Private Weekend $3550"
        CUSTOM = "custom", "Custom / small gathering"

    PACKAGE_PRICES = {
        Package.SINGLE_WEEKDAY: Decimal("799.00"),
        Package.SINGLE_WEEKEND: Decimal("999.00"),
        Package.DOUBLE_WEEKDAY: Decimal("1280.00"),
        Package.DOUBLE_WEEKEND: Decimal("1580.00"),
        Package.TRIPLE_WEEKDAY: Decimal("2150.00"),
        Package.TRIPLE_WEEKEND: Decimal("2550.00"),
        Package.PRIVATE_WEEKDAY: Decimal("3150.00"),
        Package.PRIVATE_WEEKEND: Decimal("3550.00"),
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="party_summaries")
    party_date = models.DateField()
    party_time = models.CharField(max_length=80)
    owner_name = models.CharField(max_length=200)
    owner_number = models.CharField(max_length=50)
    food_ready = models.CharField(max_length=80, blank=True)
    room_type = models.CharField(max_length=30, choices=RoomType.choices)
    kids_count = models.PositiveSmallIntegerField(default=0)
    adults_count = models.PositiveSmallIntegerField(default=0)
    deposit_method = models.CharField(max_length=100, blank=True)
    kids_name = models.CharField(max_length=250, blank=True)
    gender = models.CharField(max_length=20, choices=Gender.choices, blank=True)
    age = models.CharField(max_length=40, blank=True)
    theme = models.CharField(max_length=200, blank=True)
    balloon_color = models.CharField(max_length=200, blank=True)
    special_note = models.TextField(blank=True)
    decoration_example = models.BinaryField(null=True, blank=True, editable=False)
    decoration_example_name = models.CharField(max_length=255, blank=True)
    decoration_example_content_type = models.CharField(max_length=100, blank=True)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    package_name = models.CharField(max_length=30, choices=Package.choices)
    package_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    customer_menu_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer_menu_submitted_at = models.DateTimeField(null=True, blank=True, editable=False)
    dietary_requirements = models.TextField(blank=True)
    adult_food_avoid = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_party_summaries")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "party_summaries"
        ordering = ("party_date", "party_time")
        indexes = [
            models.Index(fields=("location", "party_date")),
            models.Index(fields=("owner_name",)),
            models.Index(fields=("owner_number",)),
        ]

    def __str__(self):
        return f"{self.owner_name} — {self.party_date}"

    @property
    def extra_food_total(self):
        total = getattr(self, "extra_food_total_value", None)
        if total is not None:
            return total or Decimal("0.00")
        return self.menu_items.filter(category=PartyMenuItem.Category.EXTRA).aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0.00")

    @property
    def total_balance(self):
        return self.package_amount - self.deposit_amount + self.extra_food_total + self.other_charges


class PartyMenuItem(models.Model):
    class Category(models.TextChoices):
        ADULT = "adult", "Adult menu"
        KIDS = "kids", "Kids menu"
        EXTRA = "extra", "Extra food"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    summary = models.ForeignKey(PartySummary, on_delete=models.CASCADE, related_name="menu_items")
    category = models.CharField(max_length=10, choices=Category.choices)
    quantity = models.CharField(max_length=40, blank=True)
    item = models.CharField(max_length=250)
    notes = models.CharField(max_length=500, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "party_menu_items"
        ordering = ("category", "position", "id")
