import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models

from accounts.models import Location


class PartySummary(models.Model):
    class RoomType(models.TextChoices):
        SINGLE = "single", "Single"
        DOUBLE_LITE = "double_lite", "Double room Lite"
        DOUBLE = "double", "Double"
        TRIPLE = "triple", "Triple"
        PRIVATE = "private", "Private"
        PRIVATE_2HOUR = "private_2hour", "Private 2 hour"
        PRIVATE_3HOUR = "private_3hour", "Private 3 hour"
        SMALL_GATHERING = "small_gathering", "Small gathering"

    class Gender(models.TextChoices):
        GIRL = "girl", "Girl"
        BOY = "boy", "Boy"
        OTHER = "other", "Other"

    class Package(models.TextChoices):
        CLASSIC_WEEKDAY = "classic_weekday", "Classic Weekday"
        SINGLE_WEEKDAY = "single_weekday", "Single Weekday"
        SINGLE_WEEKEND = "single_weekend", "Single Weekend"
        DOUBLE_LITE_WEEKDAY = "double_lite_weekday", "Double Lite Weekday"
        DOUBLE_LITE_WEEKEND = "double_lite_weekend", "Double Lite Weekend"
        DOUBLE_WEEKDAY = "double_weekday", "Double Weekday"
        DOUBLE_WEEKEND = "double_weekend", "Double Weekend"
        TRIPLE_WEEKDAY = "triple_weekday", "Triple Weekday"
        TRIPLE_WEEKEND = "triple_weekend", "Triple Weekend"
        PRIVATE_WEEKDAY = "private_weekday", "Private Weekday"
        PRIVATE_WEEKEND = "private_weekend", "Private Weekend"
        PRIVATE_WEEKDAY_2HOUR = "private_weekday_2hour", "Private Weekday 2 hour"
        PRIVATE_WEEKEND_2HOUR = "private_weekend_2hour", "Private Weekend 2 hour"
        PRIVATE_WEEKDAY_3HOUR = "private_weekday_3hour", "Private Weekday 3 hour"
        PRIVATE_WEEKEND_3HOUR = "private_weekend_3hour", "Private Weekend 3 hour"
        CUSTOM = "custom", "Custom / small gathering"

    SOUTHLAND_PACKAGE_PRICES = {
        Package.SINGLE_WEEKDAY: Decimal("699.00"),
        Package.SINGLE_WEEKEND: Decimal("899.00"),
        Package.DOUBLE_WEEKDAY: Decimal("999.00"),
        Package.DOUBLE_WEEKEND: Decimal("1299.00"),
        Package.TRIPLE_WEEKDAY: Decimal("1899.00"),
        Package.TRIPLE_WEEKEND: Decimal("2199.00"),
        Package.PRIVATE_WEEKDAY: Decimal("2699.00"),
        Package.PRIVATE_WEEKEND: Decimal("2999.00"),
    }
    CANBERRA_PACKAGE_PRICES = {
        Package.CLASSIC_WEEKDAY: Decimal("599.00"),
        Package.SINGLE_WEEKDAY: Decimal("799.00"),
        Package.SINGLE_WEEKEND: Decimal("999.00"),
        Package.DOUBLE_LITE_WEEKDAY: Decimal("1099.00"),
        Package.DOUBLE_LITE_WEEKEND: Decimal("1299.00"),
        Package.DOUBLE_WEEKDAY: Decimal("1280.00"),
        Package.DOUBLE_WEEKEND: Decimal("1580.00"),
        Package.PRIVATE_WEEKDAY_2HOUR: Decimal("1899.00"),
        Package.PRIVATE_WEEKEND_2HOUR: Decimal("2199.00"),
        Package.PRIVATE_WEEKDAY_3HOUR: Decimal("2399.00"),
        Package.PRIVATE_WEEKEND_3HOUR: Decimal("2699.00"),
    }
    # Kept as the Southland default for backwards-compatible callers.
    PACKAGE_PRICES = SOUTHLAND_PACKAGE_PRICES

    @classmethod
    def package_prices_for_location(cls, location_code):
        if location_code == Location.Code.CANBERRA:
            return cls.CANBERRA_PACKAGE_PRICES
        return cls.SOUTHLAND_PACKAGE_PRICES

    @classmethod
    def package_choices_for_location(cls, location_code):
        prices = cls.package_prices_for_location(location_code)
        labels = dict(cls.Package.choices)
        return [
            (str(package), f"{labels[str(package)]} ${amount:,.0f}")
            for package, amount in prices.items()
        ]

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
    rsvp_information = models.TextField(blank=True)
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
    voucher_menu_notes = models.TextField(blank=True)
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
    def food_voucher_amount(self):
        if self.location.code == Location.Code.CANBERRA:
            return {
                self.RoomType.SINGLE: Decimal("100.00"),
                self.RoomType.DOUBLE_LITE: Decimal("180.00"),
                self.RoomType.PRIVATE_2HOUR: Decimal("400.00"),
                self.RoomType.PRIVATE_3HOUR: Decimal("400.00"),
            }.get(self.room_type, Decimal("0.00"))
        return Decimal("0.00")

    @property
    def uses_food_voucher(self):
        return self.food_voucher_amount > 0

    @property
    def food_ordered_total(self):
        """Total priced food for voucher packages, including legacy extra rows."""
        if not self.uses_food_voucher:
            return self.extra_food_total
        return self.menu_items.filter(
            category__in=(PartyMenuItem.Category.ADULT, PartyMenuItem.Category.EXTRA)
        ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

    @property
    def extra_food_balance(self):
        chargeable_food = self.food_ordered_total if self.uses_food_voucher else self.extra_food_total
        return max(chargeable_food - self.food_voucher_amount, Decimal("0.00"))

    @property
    def custom_charges_total(self):
        return self.bill_items.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

    @property
    def total_balance(self):
        return (
            self.package_amount - self.deposit_amount + self.extra_food_balance
            + self.other_charges + self.custom_charges_total
        )


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


class PartyBillItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    summary = models.ForeignKey(PartySummary, on_delete=models.CASCADE, related_name="bill_items")
    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "party_bill_items"
        ordering = ("position", "id")


class PartyIntakeLink(models.Model):
    """A private customer form that creates or updates one party summary."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="party_intake_links")
    owner_name = models.CharField(max_length=200)
    owner_number = models.CharField(max_length=50, blank=True)
    owner_email = models.EmailField(blank=True)
    summary = models.OneToOneField(
        PartySummary, on_delete=models.SET_NULL, related_name="intake_link", null=True, blank=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_party_intake_links",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "party_intake_links"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.owner_name} — {self.location.name}"
