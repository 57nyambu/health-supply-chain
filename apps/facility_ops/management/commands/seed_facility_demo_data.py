from datetime import timedelta
import random

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save
from django.utils import timezone

from apps.accounts.models import WorkerProfile, handle_new_user
from apps.products.models import Category, Inventory, Product
from apps.warehouses.models import Branch, Warehouse
from apps.facility_ops.models import FacilityAlert, FacilityDailyStats


class Command(BaseCommand):
    help = 'Seed demo facility daily stats and alert-rich sample data for AfyaSync demos.'

    demo_password = 'AfyaSync@123'

    def _ensure_branch(self):
        branch, _ = Branch.objects.get_or_create(
            code='NRB-DEMO',
            defaults={
                'name': 'AfyaSync Nairobi Demo Branch',
                'kra_pin': 'A123456789B',
                'business_reg_no': 'BRN-DEMO-001',
                'vat_no': '',
                'county': 'NAIROBI',
                'physical_address': 'AfyaSync Demo Road, Nairobi',
                'postal_address': 'P.O. Box 10001-00100',
                'contact_phone': '+254700000001',
                'contact_email': 'branch@afyasync.dima.co.ke',
                'is_active': True,
            },
        )
        return branch

    def _ensure_warehouses(self, branch):
        warehouse_specs = [
            {
                'code': 'WH-D1',
                'name': 'Demo Main Store',
                'warehouse_type': 'DRY',
                'physical_address': 'Demo Main Store, Nairobi',
                'contact_phone': '+254700000011',
            },
            {
                'code': 'WH-D2',
                'name': 'Demo Cold Room',
                'warehouse_type': 'COLD',
                'physical_address': 'Demo Cold Room, Nairobi',
                'contact_phone': '+254700000012',
            },
            {
                'code': 'WH-D3',
                'name': 'Demo Satellite Store',
                'warehouse_type': 'DRY',
                'physical_address': 'Demo Satellite Store, Nairobi',
                'contact_phone': '+254700000013',
            },
        ]

        warehouses = []
        for spec in warehouse_specs:
            warehouse, _ = Warehouse.objects.get_or_create(
                code=spec['code'],
                defaults={
                    'branch': branch,
                    'name': spec['name'],
                    'warehouse_type': spec['warehouse_type'],
                    'physical_address': spec['physical_address'],
                    'contact_phone': spec['contact_phone'],
                    'is_active': True,
                },
            )
            warehouses.append(warehouse)

        return warehouses

    def _ensure_catalog(self):
        category, _ = Category.objects.get_or_create(
            name='Demo Medical Supplies',
            defaults={
                'description': 'Seed data for the AfyaSync demo environment.',
                'vat_category': 'STANDARD',
                'is_active': True,
            },
        )

        product_specs = [
            ('PARA-500', 'Paracetamol 500mg', 18, 30),
            ('AMOX-250', 'Amoxicillin 250mg', 24, 45),
            ('GLOVE-L', 'Latex Gloves Large', 220, 340),
            ('SYR-5ML', '5ml Syringe', 140, 220),
            ('ORS-100', 'Oral Rehydration Salts', 45, 70),
        ]

        products = []
        for sku, name, buying_price, selling_price in product_specs:
            product, _ = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    'name': name,
                    'short_name': name[:50],
                    'category': category,
                    'barcode': f'{sku}-BC',
                    'product_type': 'PHYSICAL',
                    'buying_price': buying_price,
                    'selling_price': selling_price,
                    'wholesale_price': selling_price * 0.85,
                    'reorder_level': 20,
                    'is_active': True,
                },
            )
            products.append(product)

        return products

    def _ensure_demo_users(self, branch, warehouses):
        User = get_user_model()
        demo_users = [
            {
                'email': 'admin@afyasync.dima.co.ke',
                'password': self.demo_password,
                'defaults': {
                    'first_name': 'Demo',
                    'last_name': 'Admin',
                    'phone': '+254700000101',
                    'role': 'ADMIN',
                    'is_staff': True,
                    'is_superuser': True,
                    'is_approved': True,
                },
            },
            {
                'email': 'facility@afyasync.dima.co.ke',
                'password': self.demo_password,
                'defaults': {
                    'first_name': 'Demo',
                    'last_name': 'Facility',
                    'phone': '+254700000102',
                    'role': 'BRANCH_MANAGER',
                    'is_staff': False,
                    'is_superuser': False,
                    'is_approved': True,
                },
            },
            {
                'email': 'reporter@afyasync.dima.co.ke',
                'password': self.demo_password,
                'defaults': {
                    'first_name': 'Demo',
                    'last_name': 'Reporter',
                    'phone': '+254700000103',
                    'role': 'REPORTER',
                    'is_staff': False,
                    'is_superuser': False,
                    'is_approved': True,
                },
            },
        ]

        created_users = {}
        post_save.disconnect(handle_new_user, sender=User)
        try:
            for spec in demo_users:
                user, _ = User.objects.get_or_create(email=spec['email'])
                for field, value in spec['defaults'].items():
                    setattr(user, field, value)
                user.set_password(spec['password'])
                user.save()
                created_users[spec['email']] = user
        finally:
            post_save.connect(handle_new_user, sender=User)

        facility_user = created_users['facility@afyasync.dima.co.ke']
        WorkerProfile.objects.update_or_create(
            user=facility_user,
            defaults={
                'branch': branch,
                'warehouse': warehouses[0],
                'id_number': 'ID-DEMO-001',
                'is_active': True,
            },
        )

        return created_users

    def _seed_inventory(self, warehouses, products):
        low_stock_target = warehouses[0]
        surplus_targets = warehouses[1:3]

        for index, product in enumerate(products):
            target_quantity = max(1, product.reorder_level - 2) if index == 0 else product.reorder_level + (30 * (index + 1))
            Inventory.objects.update_or_create(
                product=product,
                warehouse=low_stock_target,
                defaults={'quantity': target_quantity},
            )

            for warehouse in surplus_targets:
                Inventory.objects.update_or_create(
                    product=product,
                    warehouse=warehouse,
                    defaults={'quantity': product.reorder_level + 120 + (index * 5)},
                )

    def _seed_facility_stats(self, warehouses):
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

    def handle(self, *args, **options):
        with transaction.atomic():
            branch = self._ensure_branch()
            warehouses = self._ensure_warehouses(branch)
            products = self._ensure_catalog()
            self._ensure_demo_users(branch, warehouses)
            self._seed_facility_stats(warehouses)
            self._seed_inventory(warehouses, products)

        self.stdout.write(self.style.SUCCESS('Facility demo data seeded successfully.'))
        self.stdout.write(self.style.SUCCESS('Demo users: admin@afyasync.dima.co.ke, facility@afyasync.dima.co.ke, reporter@afyasync.dima.co.ke'))
        self.stdout.write(self.style.SUCCESS(f'Demo password: {self.demo_password}'))
