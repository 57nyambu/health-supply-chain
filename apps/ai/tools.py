from apps.analytics.models import RTInventoryAlert
from apps.facility_ops.models import FacilityAlert, FacilityDailyStats
from apps.products.models import Inventory
from apps.warehouses.models import Warehouse


def get_low_stock_alerts(warehouse_id=None, limit=10):
    qs = Inventory.objects.select_related('product', 'warehouse').all()
    if warehouse_id:
        qs = qs.filter(warehouse_id=warehouse_id)

    low_rows = [
        item for item in qs if item.quantity <= item.product.reorder_level
    ]
    low_rows.sort(key=lambda item: item.quantity)

    payload = []
    for row in low_rows[:limit]:
        payload.append({
            'product_id': row.product_id,
            'product_name': row.product.name,
            'warehouse_id': row.warehouse_id,
            'warehouse_name': row.warehouse.name,
            'current_stock': row.quantity,
            'reorder_level': row.product.reorder_level,
        })

    return payload


def get_facility_stats(warehouse_id, days=7):
    qs = FacilityDailyStats.objects.filter(warehouse_id=warehouse_id).order_by('-date')[:days]
    return [
        {
            'date': row.date.isoformat(),
            'patient_footfall': row.patient_footfall,
            'bed_occupancy_rate': row.bed_occupancy_rate,
            'attendance_rate': row.attendance_rate,
        }
        for row in qs
    ]


def get_transfer_candidates(product_id, warehouse_scope=None):
    qs = Inventory.objects.select_related('product', 'warehouse').filter(product_id=product_id)
    if warehouse_scope:
        qs = qs.filter(warehouse_id=warehouse_scope)

    if not qs:
        return []

    shortages = []
    surpluses = []
    for stock in qs:
        threshold = stock.product.reorder_level
        gap = stock.quantity - threshold
        if gap < 0:
            shortages.append((stock, abs(gap)))
        elif gap > 0:
            surpluses.append((stock, gap))

    shortages.sort(key=lambda x: x[1], reverse=True)
    surpluses.sort(key=lambda x: x[1], reverse=True)

    suggestions = []
    for short_row, short_gap in shortages:
        for surplus_row, surplus_gap in surpluses:
            if surplus_row.warehouse_id == short_row.warehouse_id:
                continue
            quantity = min(short_gap, max(0, surplus_gap // 2))
            if quantity <= 0:
                continue
            suggestions.append({
                'product': short_row.product.name,
                'from_warehouse': surplus_row.warehouse_id,
                'from_warehouse_name': surplus_row.warehouse.name,
                'to_warehouse': short_row.warehouse_id,
                'to_warehouse_name': short_row.warehouse.name,
                'suggested_quantity': quantity,
                'reasoning': (
                    f"{surplus_row.warehouse.name} holds above-threshold stock while "
                    f"{short_row.warehouse.name} is below reorder level."
                ),
            })
            break

    return suggestions


def get_underperforming_facilities(limit=10):
    qs = FacilityAlert.objects.select_related('warehouse').filter(resolved=False).order_by('-created_at')[:limit]
    return [
        {
            'warehouse_id': row.warehouse_id,
            'warehouse_name': row.warehouse.name,
            'alert_type': row.alert_type,
            'severity': row.severity,
            'message': row.message,
        }
        for row in qs
    ]


def local_forecast(warehouse_id, product_id):
    inventory = Inventory.objects.select_related('product', 'warehouse').filter(
        warehouse_id=warehouse_id,
        product_id=product_id,
    ).first()
    if not inventory:
        return None

    recent_stats = FacilityDailyStats.objects.filter(warehouse_id=warehouse_id).order_by('-date')[:7]
    if recent_stats:
        avg_footfall = sum(item.patient_footfall for item in recent_stats) / len(recent_stats)
    else:
        avg_footfall = 60

    avg_daily_consumption = max(1, int(round(avg_footfall * 0.08)))
    forecast_days_remaining = max(0, int(inventory.quantity // avg_daily_consumption))

    return {
        'product': inventory.product.name,
        'warehouse': inventory.warehouse.name,
        'current_stock': inventory.quantity,
        'avg_daily_consumption': avg_daily_consumption,
        'forecast_days_remaining': forecast_days_remaining,
        'recommendation': (
            f"Reorder soon. Estimated runout in {forecast_days_remaining} day(s) "
            f"at current demand signal."
        ),
    }


def public_facility_directory():
    rows = Warehouse.objects.select_related('branch').all()
    return [
        {
            'id': row.id,
            'name': row.name,
            'county': row.branch.county,
            'type': row.warehouse_type.lower(),
        }
        for row in rows
    ]


def public_high_severity_alerts(limit=50):
    facility_rows = FacilityAlert.objects.select_related('warehouse').filter(
        resolved=False,
        severity='high',
    ).order_by('-created_at')[:limit]

    payload = [
        {
            'facility_id': row.warehouse_id,
            'facility_name': row.warehouse.name,
            'severity': row.severity,
            'message': row.message,
            'source': 'facility_alert',
            'created_at': row.created_at,
        }
        for row in facility_rows
    ]

    inventory_rows = RTInventoryAlert.objects.select_related('warehouse', 'product').filter(
        resolved=False,
    ).order_by('-created_at')[:limit]
    for row in inventory_rows:
        payload.append({
            'facility_id': row.warehouse_id,
            'facility_name': row.warehouse.name,
            'severity': 'high',
            'message': f'Low stock: {row.product.name} ({row.current_stock})',
            'source': 'inventory_alert',
            'created_at': row.created_at,
        })

    payload.sort(key=lambda item: item['created_at'], reverse=True)
    return payload[:limit]


def public_facility_stats(facility_id):
    stats = FacilityDailyStats.objects.filter(warehouse_id=facility_id).order_by('-date')[:7]
    if not stats:
        return None

    total_footfall = sum(item.patient_footfall for item in stats)
    avg_occupancy = []
    avg_attendance = []
    for item in stats:
        if item.bed_occupancy_rate is not None:
            avg_occupancy.append(item.bed_occupancy_rate)
        if item.attendance_rate is not None:
            avg_attendance.append(item.attendance_rate)

    return {
        'facility_id': facility_id,
        'days_observed': len(stats),
        'total_patient_footfall': total_footfall,
        'avg_daily_footfall': round(total_footfall / len(stats), 1),
        'avg_bed_occupancy_rate': round(sum(avg_occupancy) / len(avg_occupancy), 1) if avg_occupancy else None,
        'avg_doctor_attendance_rate': round(sum(avg_attendance) / len(avg_attendance), 1) if avg_attendance else None,
    }
