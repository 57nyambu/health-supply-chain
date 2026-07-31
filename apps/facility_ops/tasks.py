from datetime import timedelta

from celery import shared_task
from django.db.models import Avg
from django.utils import timezone

from apps.integrations.services import NotificationService

from .models import FacilityAlert, FacilityDailyStats


@shared_task
def flag_underperforming_facilities(days=3):
    """Create unresolved under-staffing alerts for facilities trending below target attendance."""
    start_date = timezone.now().date() - timedelta(days=days)
    recent_qs = FacilityDailyStats.objects.filter(date__gte=start_date).values('warehouse').annotate(
        avg_attendance=Avg('doctors_present'),
        avg_scheduled=Avg('doctors_scheduled'),
    )

    created_count = 0
    notification_service = NotificationService()

    for item in recent_qs:
        scheduled = item.get('avg_scheduled') or 0
        present = item.get('avg_attendance') or 0
        if scheduled <= 0:
            continue

        attendance_ratio = present / scheduled
        if attendance_ratio >= 0.7:
            continue

        warehouse_id = item['warehouse']
        exists = FacilityAlert.objects.filter(
            warehouse_id=warehouse_id,
            alert_type='understaffed',
            resolved=False,
        ).exists()
        if exists:
            continue

        alert = FacilityAlert.objects.create(
            warehouse_id=warehouse_id,
            alert_type='understaffed',
            severity='high',
            message=(
                f'Only {present:.1f} of {scheduled:.1f} scheduled doctors have been present '
                f'on average over the last {days} days.'
            ),
        )
        created_count += 1

        warehouse = alert.warehouse
        manager = getattr(warehouse, 'manager', None)
        if manager and manager.email:
            notification_service.send_notification(
                user=manager,
                notification_type='email',
                subject=f'Facility Alert: {warehouse.name}',
                message=alert.message,
            )

    return created_count
