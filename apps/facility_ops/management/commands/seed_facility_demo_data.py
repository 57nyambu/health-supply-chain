from datetime import timedelta
import random

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.facility_ops.models import FacilityAlert, FacilityDailyStats
from apps.products.models import Inventory, Product
from apps.warehouses.models import Warehouse


class Command(BaseCommand):
    help = 'Seed demo facility daily stats and alert-rich sample data for AfyaSync demos.'

    def handle(self, *args, **options):
        warehouses = list(Warehouse.objects.all()[:5])
        if not warehouses:
            self.stdout.write(self.style.WARNING('No warehouses found. Seed warehouses first.'))
            return

        products = list(Product.objects.all()[:3])
        today = timezone.now().date()

        for idx, warehouse in enumerate(warehouses):
            for day_offset in range(30):
                sample_date = today - timedelta(days=day_offset)

                footfall_base = 130 - (idx * 8)
                beds_total = 40
                doctors_scheduled = 5

                if idx == 0:
                    doctors_present = random.choice([2, 3])
                    footfall = random.randint(80, 105)
                    beds_occupied = random.randint(34, 40)
                elif idx in (1, 2):
                    doctors_present = random.choice([4, 5])
                    footfall = random.randint(120, 160)
                    beds_occupied = random.randint(26, 34)
                else:
                    doctors_present = random.choice([3, 4, 5])
                    footfall = random.randint(max(60, footfall_base - 20), footfall_base + 15)
                    beds_occupied = random.randint(22, 36)

                FacilityDailyStats.objects.update_or_create(
                    warehouse=warehouse,
                    date=sample_date,
                    defaults={
                        'patient_footfall': footfall,
                        'beds_total': beds_total,
                        'beds_occupied': beds_occupied,
                        'doctors_scheduled': doctors_scheduled,
                        'doctors_present': doctors_present,
                    },
                )

            if idx == 0:
                FacilityAlert.objects.get_or_create(
                    warehouse=warehouse,
                    alert_type='understaffed',
                    message='Only 3 of 5 scheduled doctors present for multiple days.',
                    defaults={'severity': 'high', 'resolved': False},
                )

        if products:
            low_stock_target = warehouses[0]
            surplus_targets = warehouses[1:3]
            demo_product = products[0]

            Inventory.objects.update_or_create(
                product=demo_product,
                warehouse=low_stock_target,
                defaults={'quantity': max(1, demo_product.reorder_level - 2)},
            )

            for w in surplus_targets:
                Inventory.objects.update_or_create(
                    product=demo_product,
                    warehouse=w,
                    defaults={'quantity': demo_product.reorder_level + 120},
                )

        self.stdout.write(self.style.SUCCESS('Facility demo data seeded successfully.'))
