"""Access-control data: permission catalogue and roles (DESIGN §7)."""

from django.db import models

from apps.access.catalogue import Sensitivity
from apps.access.roles import ChartAccess


class Permission(models.Model):
    """Database mirror of a code-defined PermissionDef (synced by ``sync_access``)."""

    code = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255)
    sensitivity = models.CharField(max_length=20, choices=[(s.value, s.value) for s in Sensitivity])
    requires_licence = models.BooleanField(default=False)
    privileged = models.BooleanField(default=False)
    active = models.BooleanField(
        default=True, help_text="False once the code is removed from the catalogue"
    )

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class Role(models.Model):
    CHART_CHOICES = [(level.value, level.value) for level in ChartAccess]

    code = models.CharField(max_length=60, unique=True)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    permissions = models.ManyToManyField(Permission, related_name="roles", blank=True)
    chart_baseline = models.CharField(
        max_length=20, choices=CHART_CHOICES, default=ChartAccess.NONE
    )
    chart_care_team = models.CharField(
        max_length=20, choices=CHART_CHOICES, default=ChartAccess.NONE
    )
    privileged = models.BooleanField(
        default=False, help_text="Granting it needs a second facility admin"
    )
    mfa_required = models.BooleanField(default=False)
    addon = models.BooleanField(
        default=False, help_text="Supervisor add-on assigned on top of a base role"
    )
    requires_cosign = models.BooleanField(default=False)
    service_account = models.BooleanField(default=False)
    is_system = models.BooleanField(default=True, help_text="Seeded from apps/access/roles.py")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
