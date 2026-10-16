import datetime

import factory

from apps.facilities.tests.factories import FacilityFactory
from apps.patients.models import Patient


class PatientFactory(factory.django.DjangoModelFactory[Patient]):
    """Synthetic patients only (never real names or identifiers)."""

    class Meta:
        model = Patient

    facility = factory.SubFactory(FacilityFactory)
    mrn = factory.Sequence(lambda n: f"TEST-{n:06d}")
    given_name = "Synthetic"
    family_name = factory.Sequence(lambda n: f"Patient{n}")
    sex = Patient.Sex.FEMALE
    date_of_birth = datetime.date(1990, 1, 1)
