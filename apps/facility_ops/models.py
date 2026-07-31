from django.db import models
from apps.core.models import BaseModel


class FacilityDailyStats(BaseModel):
    """
    One row per facility per day. Deliberately flat (not 3 separate
    footfall/bed/attendance tables) to keep seeding, querying, and the
    Gemma prompt payload simple — see GEMMA4_HACKATHON_PLAN.md for the
    reasoning behind this call.
    """
    warehouse = models.ForeignKey(
        'warehouses.Warehouse', on_delete=models.CASCADE,
        related_name='daily_stats',
        verbose_name="Health Facility",
    )
    date = models.DateField()

    patient_footfall = models.PositiveIntegerField(default=0)
    beds_total = models.PositiveIntegerField(default=0)
    beds_occupied = models.PositiveIntegerField(default=0)
    doctors_scheduled = models.PositiveIntegerField(default=0)
    doctors_present = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Facility Daily Stats"
        verbose_name_plural = "Facility Daily Stats"
        unique_together = ('warehouse', 'date')
        ordering = ['-date']
        indexes = [models.Index(fields=['warehouse', 'date'])]

    def __str__(self):
        return f"{self.warehouse.name} — {self.date}"

    @property
    def bed_occupancy_rate(self):
        if not self.beds_total:
            return None
        return round(self.beds_occupied / self.beds_total * 100, 1)

    @property
    def attendance_rate(self):
        if not self.doctors_scheduled:
            return None
        return round(self.doctors_present / self.doctors_scheduled * 100, 1)


class FacilityAlert(BaseModel):
    ALERT_TYPES = [
        ('understaffed', 'Understaffed'),
        ('low_footfall', 'Low Footfall'),
        ('overcrowded', 'Overcrowded'),
        ('stockout_risk', 'Stock-Out Risk'),
        ('custom', 'Custom'),
    ]
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    warehouse = models.ForeignKey(
        'warehouses.Warehouse', on_delete=models.CASCADE,
        related_name='facility_alerts',
        verbose_name="Health Facility",
    )
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    message = models.TextField(help_text="Gemma-generated or manually entered narrative")
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default='medium')
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Facility Alert"
        ordering = ['-created_at']
        indexes = [models.Index(fields=['warehouse', 'resolved'])]

    def __str__(self):
        return f"[{self.severity}] {self.warehouse.name}: {self.get_alert_type_display()}"