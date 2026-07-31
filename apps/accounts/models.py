from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator, RegexValidator
from apps.core.models import BaseModel, AuditLog
from django.contrib.auth.models import BaseUserManager
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.integrations.tasks import send_welcome_credentials_task

class UserManager(BaseUserManager):
    """Enhanced user manager with better validation"""
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_approved', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser, BaseModel):
    """Extended User model with security enhancements"""
    
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('System Administrator')
        BRANCH_MANAGER = 'BRANCH_MANAGER', _('Branch Manager')
        PROCUREMENT = 'PROCUREMENT', _('Procurement Officer')
        WAREHOUSE = 'WAREHOUSE', _('Warehouse Staff')
        CASHIER = 'CASHIER', _('Cashier')
        REPORTER = 'REPORTER', _('Reports Viewer')
    
    username = None
    email = models.EmailField(_('email address'), unique=True)
    phone = models.CharField(
        max_length=15,
        unique=True,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')]
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CASHIER)
    is_approved = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    account_locked = models.BooleanField(default=False)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']
        permissions = [
            ('manage_workers', 'Can create/edit workers'),
            ('approve_workers', 'Can approve worker accounts'),
            ('view_dashboard', 'Can view admin dashboard'),
            ('reset_password', 'Can reset user passwords'),
        ]

    def __str__(self):
        return f"{self.get_full_name() or self.email} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            AuditLog.objects.create(
                user=self.created_by if hasattr(self, 'created_by') else None,
                action='CREATE',
                model='User',
                object_id=self.pk,
                details={
                    'email': self.email,
                    'role': self.role,
                    'approved': self.is_approved
                }
            )

class WorkerProfile(BaseModel):
    """Extended worker information with branch association"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    branch = models.ForeignKey('warehouses.Branch', on_delete=models.PROTECT)
    id_number = models.CharField(max_length=20, blank=True)
    signature = models.ImageField(
        upload_to='signatures/%Y/%m/',
        blank=True,
        validators=[FileExtensionValidator(['png', 'jpg', 'jpeg'])]
    )
    is_active = models.BooleanField(default=True)
    pin_code = models.CharField(max_length=6, blank=True, null=True)  # For POS quick login

    def __str__(self):
        return f"{self.user.email} profile"

    class Meta:
        verbose_name = _('worker profile')
        verbose_name_plural = _('worker profiles')

# Signals
@receiver(post_save, sender=User)
def handle_new_user(sender, instance, created, **kwargs):
    if created and not instance.is_superuser:
        # Send credentials to new workers
        send_welcome_credentials_task.delay(instance.id)