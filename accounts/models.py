import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class Location(models.Model):
    class Code(models.TextChoices):
        SOUTHLAND = "southland", "Little Amigos Southland"
        CANBERRA = "canberra", "Little Amigos Canberra"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, choices=Code.choices, unique=True)
    name = models.CharField(max_length=100, unique=True)
    timezone = models.CharField(max_length=64, default="Australia/Sydney")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "locations"

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, display_name, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email).strip().lower()
        user = self.model(email=email, display_name=display_name, **extra_fields)
        if password:
            user.set_password(password)
            user.password_reset_required = True
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, display_name, password, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, display_name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        STAFF = "staff", "Staff"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=150)
    role = models.CharField(max_length=10, choices=Role.choices)
    location = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="users",
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    password_reset_required = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["display_name"]

    class Meta:
        db_table = "users"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(role="admin", location__isnull=True)
                    | models.Q(role="staff", location__isnull=False)
                ),
                name="users_role_location_check",
            )
        ]

    def __str__(self):
        return f"{self.display_name} <{self.email}>"


class SouthlandShowcaseTheme(models.Model):
    class Category(models.TextChoices):
        MAGIC = "magic", "Magic & wonder"
        ADVENTURE = "adventure", "Adventure"
        FAVOURITES = "favourites", "Favourites"
        CUSTOM = "custom", "Custom"

    name = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.FAVOURITES)
    search_terms = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name


class SouthlandShowcaseThemePhoto(models.Model):
    theme = models.ForeignKey(SouthlandShowcaseTheme, on_delete=models.CASCADE, related_name="photos")
    static_path = models.CharField(max_length=255, blank=True)
    image_data = models.BinaryField(null=True, blank=True, editable=False)
    image_name = models.CharField(max_length=255, blank=True)
    image_content_type = models.CharField(max_length=100, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")


class SouthlandShowcaseAddon(models.Model):
    name = models.CharField(max_length=120)
    price_label = models.CharField(max_length=120)
    price_from = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    details = models.TextField(blank=True)
    static_path = models.CharField(max_length=255, blank=True)
    image_data = models.BinaryField(null=True, blank=True, editable=False)
    image_name = models.CharField(max_length=255, blank=True)
    image_content_type = models.CharField(max_length=100, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name


class SouthlandShowcaseInvite(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer_name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    party_date = models.DateField(null=True, blank=True)
    estimated_guest_count = models.PositiveIntegerField(null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="southland_showcase_invites",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.customer_name} · {self.party_date or 'date TBC'}"
