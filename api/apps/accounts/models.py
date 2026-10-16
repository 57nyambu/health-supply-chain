from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class UserManager(BaseUserManager):
    """Enhanced user manager with better validation"""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_approved", True)
        extra_fields.setdefault("role", User.Role.ADMIN)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser, BaseModel):
    """Extended User model with security enhancements"""

    class Role(models.TextChoices):
        ADMIN = "ADMIN", _("System Administrator")
        BRANCH_MANAGER = "BRANCH_MANAGER", _("Branch Manager")
        PROCUREMENT = "PROCUREMENT", _("Procurement Officer")
        WAREHOUSE = "WAREHOUSE", _("Warehouse Staff")
        CASHIER = "CASHIER", _("Cashier")
        REPORTER = "REPORTER", _("Reports Viewer")

    username = None  # type: ignore[assignment]  # e-mail is the login
    email = models.EmailField(_("email address"), unique=True)
    phone = models.CharField(
        max_length=15,
        unique=True,
        blank=True,
        null=True,
        validators=[RegexValidator(r"^\+?1?\d{9,15}$")],
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CASHIER)
    is_approved = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    account_locked = models.BooleanField(default=False)
    last_failed_login_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    must_change_password = models.BooleanField(default=False)
    password_changed_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()  # type: ignore[misc, assignment]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-date_joined"]
        permissions = [
            ("manage_workers", "Can create/edit workers"),
            ("approve_workers", "Can approve worker accounts"),
            ("view_dashboard", "Can view admin dashboard"),
            ("reset_password", "Can reset user passwords"),
        ]

    def __str__(self):
        return f"{self.get_full_name() or self.email} ({self.get_role_display()})"


class WorkerProfile(BaseModel):
    """Extended worker information with branch association"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    branch = models.ForeignKey("warehouses.Branch", on_delete=models.PROTECT)
    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_staff",
        help_text="Facility assignment for Tier-2 scoped dashboards and AI endpoints.",
    )
    id_number = models.CharField(max_length=20, blank=True)
    signature = models.ImageField(
        upload_to="signatures/%Y/%m/",
        blank=True,
        validators=[FileExtensionValidator(["png", "jpg", "jpeg"])],
    )
    is_active = models.BooleanField(default=True)
    # Legacy plaintext POS PIN; replaced by a hashed workstation PIN in P1-UAC-06.
    pin_code = models.CharField(max_length=6, blank=True, null=True)  # noqa: DJ001

    def __str__(self):
        return f"{self.user.email} profile"

    class Meta:
        verbose_name = _("worker profile")
        verbose_name_plural = _("worker profiles")


class UserSession(models.Model):
    """One login on one browser/device: lets the server end every session of a user at once."""

    class EndReason(models.TextChoices):
        LOGOUT = "logout", "Logged out"
        IDLE = "idle", "Idle timeout"
        ABSOLUTE = "absolute", "Absolute timeout"
        REVOKED = "revoked", "Revoked by an administrator"
        DEACTIVATED = "deactivated", "User deactivated"
        SWITCHED = "switched", "Workstation switched user"

    session_key = models.CharField(max_length=40, db_index=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="sessions")
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    end_reason = models.CharField(max_length=20, choices=EndReason.choices, blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["user", "ended_at"])]

    def __str__(self):
        return f"session of user {self.user_id} ({'open' if self.ended_at is None else self.end_reason})"
