from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import EncryptedTextField
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
    # Workstation quick-switch PIN (DESIGN §7.2): 6 digits, stored as an argon2id hash.
    pin_hash = models.CharField(max_length=200, blank=True, default="")
    pin_set_at = models.DateTimeField(null=True, blank=True)
    pin_failures = models.PositiveSmallIntegerField(default=0)

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


class MfaDevice(models.Model):
    """A TOTP authenticator (DESIGN §7.2). The shared secret is encrypted at rest."""

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="mfa_devices")
    secret = EncryptedTextField()
    confirmed_at = models.DateTimeField(null=True, blank=True)
    last_used_counter = models.BigIntegerField(
        default=0, help_text="Highest TOTP step accepted (replay guard)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    removed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"TOTP device of user {self.user_id} ({'active' if self.confirmed_at else 'pending'})"
        )


class RecoveryCode(models.Model):
    """Single-use MFA recovery code; only an HMAC of the code is stored."""

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="recovery_codes")
    code_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"recovery code of user {self.user_id} ({'used' if self.used_at else 'unused'})"


class WorkstationSession(models.Model):
    """A full (password, and MFA where required) sign-in of a user on a shared workstation.

    For 12 hours afterwards the user may unlock or switch in on that workstation with
    their PIN instead of the password (DESIGN §7.2).
    """

    workstation_id = models.CharField(max_length=64, db_index=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="workstation_sessions")
    signed_in_at = models.DateTimeField()
    mfa_verified = models.BooleanField(default=False)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-signed_in_at"]

    def __str__(self):
        return f"user {self.user_id} on workstation {self.workstation_id[:8]}"


class ProfessionalLicence(models.Model):
    """A practising licence from a Kenyan regulator (DESIGN §7.10, KE-PRF-01).

    Clinical permissions (``requires_licence``) need a licence that is valid on the day
    and issued by a regulator the granting role accepts.
    """

    class Regulator(models.TextChoices):
        KMPDC = "KMPDC", "Kenya Medical Practitioners and Dentists Council"
        COC = "COC", "Clinical Officers Council"
        NCK = "NCK", "Nursing Council of Kenya"
        PPB = "PPB", "Pharmacy and Poisons Board"
        KMLTTB = "KMLTTB", "Kenya Medical Laboratory Technicians and Technologists Board"
        OTHER = "OTHER", "Other regulator"

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="licences")
    regulator = models.CharField(max_length=10, choices=Regulator.choices)
    registration_number = models.CharField(max_length=50)
    licence_number = models.CharField(max_length=50, blank=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField()
    puid = models.CharField("Health Worker Registry PUID", max_length=40, blank=True)
    slade_code = models.CharField(max_length=50, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_source = models.CharField(max_length=40, blank=True)
    expiry_notified_for = models.DateField(
        null=True, blank=True, help_text="valid_to date the 30-day warning was sent for"
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user", "regulator", "-valid_to"]
        constraints = [
            models.UniqueConstraint(
                fields=["regulator", "registration_number", "valid_to"],
                name="accounts_licence_unique_period",
            ),
        ]

    def __str__(self):
        return f"{self.regulator} licence of user {self.user_id} (to {self.valid_to})"
