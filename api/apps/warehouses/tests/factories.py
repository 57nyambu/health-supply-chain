import factory

from apps.facilities.tests.factories import BranchFactory
from apps.products.models import Category, Inventory, Product
from apps.warehouses.models import Warehouse


class WarehouseFactory(factory.django.DjangoModelFactory[Warehouse]):
    class Meta:
        model = Warehouse

    branch = factory.SubFactory(BranchFactory)
    name = factory.Sequence(lambda n: f"Store {n}")
    code = factory.Sequence(lambda n: f"WH-{n:04d}")
    physical_address = "Synthetic store"
    contact_phone = "+254700000001"


class CategoryFactory(factory.django.DjangoModelFactory[Category]):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")


class ProductFactory(factory.django.DjangoModelFactory[Product]):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"Paracetamol 500mg #{n}")
    category = factory.SubFactory(CategoryFactory)
    sku = factory.Sequence(lambda n: f"SKU-T-{n:05d}")
    barcode = factory.Sequence(lambda n: f"BC{n:08d}")
    buying_price = "10.00"
    selling_price = "15.00"
    reorder_level = 20


class InventoryFactory(factory.django.DjangoModelFactory[Inventory]):
    class Meta:
        model = Inventory

    product = factory.SubFactory(ProductFactory)
    warehouse = factory.SubFactory(WarehouseFactory)
    quantity = 50
