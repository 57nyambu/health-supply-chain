import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import User
from apps.warehouses.models import Warehouse


@pytest.mark.django_db
def test_seed_loads_synthetic_data_idempotently(settings, monkeypatch):
    from apps.access.models import Role, RoleAssignment
    from apps.accounts.models import ProfessionalLicence
    from apps.facilities.models import Bed, Facility, ServicePoint
    from apps.patients import seed as patient_seed
    from apps.patients.models import Patient, PatientIdentifier

    settings.DJANGO_ENV = "dev"
    monkeypatch.setattr(patient_seed, "COUNT", 6)
    call_command("seed")
    call_command("seed")
    assert Warehouse.objects.filter(code__startswith="WH-D").count() == 3
    admin = User.objects.get(email="admin@afyasync.dima.co.ke")
    assert admin.check_password(settings.SEED_PASSWORD)

    site = Facility.objects.get(mfl_code="99999")
    assert site.keph_level == 4
    assert ServicePoint.objects.filter(facility=site).count() == 9
    assert Bed.objects.filter(ward__facility=site).count() == 26
    roles = Role.objects.filter(active=True, service_account=False)
    assert RoleAssignment.objects.filter(facility=site, status="active").count() == roles.count()
    reception = User.objects.get(email="receptionist@seed.afyasync.test")
    assert reception.check_password(settings.SEED_PASSWORD)
    assert ProfessionalLicence.objects.filter(
        user__email="clinical_officer@seed.afyasync.test", regulator="COC"
    ).exists()
    assert Patient.objects.filter(facility=site).count() == 6
    identifiers = PatientIdentifier.objects.filter(patient__facility=site, type="national_id")
    assert all(row.value.startswith("000") for row in identifiers)

    # Operations data for the reports and inventory workspaces (P1-WEB-06), once.
    from apps.analytics.models import RTInventoryAlert
    from apps.facility_ops.models import FacilityAlert, FacilityDailyStats
    from apps.warehouses.selectors import facility_warehouses

    stores = facility_warehouses(site.pk)
    assert list(stores.values_list("code", flat=True)) == ["SYN-MAIN"]
    assert FacilityDailyStats.objects.filter(warehouse__in=stores).count() == 7
    assert FacilityAlert.objects.filter(warehouse__in=stores).count() == 1
    assert RTInventoryAlert.objects.filter(warehouse__in=stores).count() == 1

    # Payers, schemes and synthetic cover (the seam Phase 2 and Phase 3 share, ADR-024).
    from apps.insurance.models import Coverage, Payer

    assert Payer.objects.filter(code="sha").exists()
    covered = Coverage.objects.filter(patient__facility=site)
    assert covered.count() == 2  # patients 3 and 6 of 6 have SHA SHIF cover
    assert all(c.member_number.startswith("SHA-SYN-") for c in covered)


@pytest.mark.django_db
def test_seed_refuses_in_production(settings):
    settings.DJANGO_ENV = "prod"
    with pytest.raises(CommandError, match="DJANGO_ENV=prod"):
        call_command("seed")


@pytest.mark.django_db
def test_seed_requires_a_seed_password(settings):
    settings.DJANGO_ENV = "dev"
    settings.SEED_PASSWORD = ""
    with pytest.raises(CommandError, match="SEED_PASSWORD"):
        call_command("seed")


@pytest.mark.django_db
def test_reset_dev_refuses_outside_dev(settings):
    settings.DJANGO_ENV = "test"
    with pytest.raises(CommandError, match="DJANGO_ENV=dev"):
        call_command("reset_dev", "--yes")


@pytest.mark.django_db
def test_reset_dev_needs_confirmation(settings):
    settings.DJANGO_ENV = "dev"
    settings.DEBUG = True
    with pytest.raises(CommandError, match="--yes"):
        call_command("reset_dev")


@pytest.mark.django_db
def test_reset_dev_refuses_a_data_dir_outside_the_repository(settings, tmp_path_factory):
    settings.DJANGO_ENV = "dev"
    settings.DEBUG = True
    settings.DATA_DIR = tmp_path_factory.mktemp("elsewhere")
    with pytest.raises(CommandError, match="outside the repository"):
        call_command("reset_dev", "--yes")


@pytest.mark.django_db(transaction=True)
def test_reset_dev_flushes_and_removes_objects(settings):
    data_dir = settings.REPO_ROOT / "data" / "test-reset-dev"
    objects = data_dir / "objects"
    objects.mkdir(parents=True, exist_ok=True)
    (objects / "blob").write_bytes(b"x")
    (data_dir / "keep.txt").write_bytes(b"kept")
    settings.DJANGO_ENV = "dev"
    settings.DEBUG = True
    settings.DATA_DIR = data_dir
    User.objects.create_user(email="someone@example.test")
    try:
        call_command("reset_dev", "--yes")
        assert not User.objects.exists()
        assert not objects.exists()
        assert (data_dir / "keep.txt").exists()
    finally:
        (data_dir / "keep.txt").unlink(missing_ok=True)
        data_dir.rmdir()
