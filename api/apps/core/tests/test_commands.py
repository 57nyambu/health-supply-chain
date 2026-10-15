import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import User
from apps.warehouses.models import Warehouse


@pytest.mark.django_db
def test_seed_loads_synthetic_data_idempotently(settings):
    settings.DJANGO_ENV = "dev"
    call_command("seed")
    call_command("seed")
    assert Warehouse.objects.filter(code__startswith="WH-D").count() == 3
    admin = User.objects.get(email="admin@afyasync.dima.co.ke")
    assert admin.check_password(settings.SEED_PASSWORD)


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
