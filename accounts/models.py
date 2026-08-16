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
