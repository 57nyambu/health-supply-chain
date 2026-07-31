from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import AuditLog

User = get_user_model()

@receiver(post_save, sender=User)
def log_user_changes(sender, instance, created, **kwargs):
    action = 'CREATE' if created else 'UPDATE'
    AuditLog.objects.create(
        user=instance,
        action=action,
        model='User',
        object_id=instance.pk,
        details={
            'email': instance.email,
            'role': instance.role,
            'approved': instance.is_approved
        }
    )

@receiver(pre_save, sender=User)
def check_account_lock(sender, instance, **kwargs):
    if instance.pk:
        original = User.objects.get(pk=instance.pk)
        if original.failed_login_attempts >= 5 and not instance.account_locked:
            instance.account_locked = True