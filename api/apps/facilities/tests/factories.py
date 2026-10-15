import factory

from apps.facilities.models import Bed, Department, Facility, ServicePoint, Ward
from apps.warehouses.models import Branch


class BranchFactory(factory.django.DjangoModelFactory[Branch]):
    class Meta:
        model = Branch

    name = factory.Sequence(lambda n: f"Synthetic Branch {n}")
    code = factory.Sequence(lambda n: f"SB{n:04d}")
    kra_pin = "P000000000A"
    business_reg_no = factory.Sequence(lambda n: f"BRN-{n:05d}")
    county = "NAIROBI"
    physical_address = "Synthetic Road, Nairobi"
    contact_phone = "+254700000000"


class FacilityFactory(factory.django.DjangoModelFactory[Facility]):
    class Meta:
        model = Facility

    branch = factory.SubFactory(BranchFactory)
    name = factory.LazyAttribute(lambda o: o.branch.name)
    mfl_code = factory.Sequence(lambda n: f"{90000 + n}")
    keph_level = Facility.KephLevel.LEVEL_4


class DepartmentFactory(factory.django.DjangoModelFactory[Department]):
    class Meta:
        model = Department

    facility = factory.SubFactory(FacilityFactory)
    code = factory.Sequence(lambda n: f"D{n}")
    name = factory.Sequence(lambda n: f"Department {n}")


class ServicePointFactory(factory.django.DjangoModelFactory[ServicePoint]):
    class Meta:
        model = ServicePoint

    facility = factory.SubFactory(FacilityFactory)
    code = factory.Sequence(lambda n: f"SP{n}")
    name = factory.Sequence(lambda n: f"Service point {n}")
    kind = ServicePoint.Kind.CONSULTATION


class WardFactory(factory.django.DjangoModelFactory[Ward]):
    class Meta:
        model = Ward

    facility = factory.SubFactory(FacilityFactory)
    code = factory.Sequence(lambda n: f"W{n}")
    name = factory.Sequence(lambda n: f"Ward {n}")


class BedFactory(factory.django.DjangoModelFactory[Bed]):
    class Meta:
        model = Bed

    ward = factory.SubFactory(WardFactory)
    code = factory.Sequence(lambda n: f"B{n}")
