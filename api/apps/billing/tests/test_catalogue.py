"""P2-BIL-01: service catalogue, effective-dated price lists, resolution, maker-checker."""

from datetime import timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.access import approvals
from apps.access.models import ApprovalRequest
from apps.audit.models import AuditEvent
from apps.billing import seed, services
from apps.billing.models import PriceList, PriceListItem, Service
from apps.insurance.seed import payers_and_schemes

pytestmark = pytest.mark.django_db
URL = "/api/v1/billing/"


@pytest.fixture
def schemes():
    return payers_and_schemes()


@pytest.fixture
def lists(facility, schemes):
    shif = schemes["sha/shif"]
    return {
        "cash": services.create_price_list(facility=facility, actor=None, code="cash", name="Cash"),
        "shif": services.create_price_list(
            facility=facility, actor=None, code="shif", name="SHIF", scheme=shif
        ),
        "sha": services.create_price_list(
            facility=facility, actor=None, code="sha", name="SHA default", payer=shif.payer
        ),
    }


@pytest.fixture
def fbc(facility):
    return services._create_service(
        facility=facility, actor=None, code="lab-fbc", name="Full blood count", kind="lab"
    )


def price(price_list, service, amount, start):
    return services._set_price(
        price_list=price_list,
        service=service,
        price=Decimal(amount),
        effective_from=start,
        actor=None,
    )


def test_service_carries_sha_and_etims_mapping_fields(facility):
    service = services._create_service(
        facility=facility,
        actor=None,
        code="img-cxr",
        name="Chest X-ray",
        kind="imaging",
        revenue_code="REV-IMG",
        sha_interventions=["syn-sha-img-001", "SYN-SHA-IMG-001", " syn-x "],
        etims_item_code="KE1NTXU0000001",
    )
    assert service.code == "IMG-CXR"
    assert service.sha_interventions == ["SYN-SHA-IMG-001", "SYN-X"]
    assert service.etims_item_code == "KE1NTXU0000001"
    with pytest.raises(ValidationError):
        services._create_service(
            facility=facility, actor=None, code="IMG-CXR", name="x", kind="lab"
        )
    with pytest.raises(ValidationError):
        services._create_service(facility=facility, actor=None, code="Z", name="x", kind="nope")


def test_resolution_order_is_scheme_then_payer_then_cash(facility, schemes, lists, fbc):
    today = timezone.localdate()
    shif, phc = schemes["sha/shif"], schemes["sha/phc"]
    insurer = schemes["syn-insurer-a/gold"]
    price(lists["cash"], fbc, "800.00", today)
    assert services.resolve_price(fbc).amount == Decimal("800.00")
    assert services.resolve_price(fbc, scheme=shif).basis == "cash"  # nothing more specific
    price(lists["sha"], fbc, "650.00", today)
    assert services.resolve_price(fbc, scheme=phc).amount == Decimal("650.00")  # payer default
    price(lists["shif"], fbc, "600.00", today)
    quote = services.resolve_price(fbc, scheme=shif)
    assert (quote.amount, quote.basis, quote.price_list_id) == (
        Decimal("600.00"),
        "scheme",
        lists["shif"].pk,
    )
    assert services.resolve_price(fbc, scheme=insurer).basis == "cash"  # other payer → cash


def test_prices_are_effective_dated_and_history_is_kept(facility, lists, fbc):
    today = timezone.localdate()
    first = price(lists["cash"], fbc, "700.00", today - timedelta(days=30))
    price(lists["cash"], fbc, "800.00", today + timedelta(days=10))
    first.refresh_from_db()
    assert first.effective_to == today + timedelta(days=9)
    assert services.resolve_price(fbc).amount == Decimal("700.00")
    assert services.resolve_price(fbc, on=today + timedelta(days=10)).amount == Decimal("800.00")
    assert services.resolve_price(fbc, on=today - timedelta(days=30)).amount == Decimal("700.00")
    with pytest.raises(services.NoPrice):
        services.resolve_price(fbc, on=today - timedelta(days=31))
    with pytest.raises(ValidationError, match="start after"):
        price(lists["cash"], fbc, "900.00", today)  # before the open (future) row started
    assert PriceListItem.objects.filter(service=fbc).count() == 2


def test_price_change_goes_through_finance_approval(facility, lists, fbc, staff):
    today = timezone.localdate()
    price(lists["cash"], fbc, "800.00", today - timedelta(days=5))
    officer, manager = staff("billing_officer"), staff("finance_manager")
    request = services.request_price_change(
        price_list=lists["cash"],
        service=fbc,
        price="850.00",
        effective_from=None,
        actor=officer,
        reason="Reagent costs went up",
    )
    assert services.resolve_price(fbc).amount == Decimal("800.00")  # not until approved
    with pytest.raises(PermissionDenied):
        approvals.approve(request, approver=officer)  # never one's own request
    with pytest.raises(PermissionDenied):
        approvals.approve(request, approver=staff("billing_officer"))  # not an approver
    approvals.approve(request, approver=manager)
    assert services.resolve_price(fbc).amount == Decimal("850.00")
    item = PriceListItem.objects.get(service=fbc, effective_to__isnull=True)
    assert item.approval_id == request.pk
    event = AuditEvent.objects.filter(action="billing.price.set").latest("ts")
    assert event.detail["previous"] == "800.00" and event.detail["price"] == "850.00"


def test_price_change_rules(facility, lists, fbc, staff):
    officer = staff("billing_officer")
    with pytest.raises(ValidationError, match="past"):
        services.request_price_change(
            price_list=lists["cash"],
            service=fbc,
            price="1.00",
            effective_from=timezone.localdate() - timedelta(days=1),
            actor=officer,
            reason="x",
        )
    with pytest.raises(PermissionDenied):
        services.request_price_change(
            price_list=lists["cash"],
            service=fbc,
            price="1.00",
            effective_from=None,
            actor=staff("cashier"),
            reason="x",
        )


def test_new_service_needs_approval_and_gets_its_cash_price(facility, lists, staff):
    officer, manager = staff("billing_officer"), staff("finance_manager")
    request = services.request_new_service(
        facility=facility,
        actor=officer,
        reason="New test offered",
        code="lab-crp",
        name="C-reactive protein",
        kind="lab",
        cash_price="900",
    )
    assert not Service.objects.filter(code="LAB-CRP").exists()
    approvals.approve(request, approver=manager)
    service = Service.objects.get(code="LAB-CRP")
    assert service.active
    assert services.resolve_price(service).amount == Decimal("900.00")


def test_price_list_cannot_be_for_payer_and_scheme(facility, schemes):
    shif = schemes["sha/shif"]
    with pytest.raises(ValidationError):
        services.create_price_list(
            facility=facility, actor=None, code="x", name="x", payer=shif.payer, scheme=shif
        )


def test_api_catalogue_quote_and_change_request(api_as, facility, lists, fbc, staff):
    price(lists["cash"], fbc, "800.00", timezone.localdate())
    clinician = api_as("clinical_officer", facility=facility)
    rows = clinician.get(URL + "services/?kind=lab").json()["results"]
    assert [r["code"] for r in rows] == ["LAB-FBC"]
    quote = clinician.get(URL + f"quote/?service={fbc.pk}").json()
    assert quote == {
        "service": str(fbc.pk),
        "amount": "800.00",
        "basis": "cash",
        "price_list": str(lists["cash"].pk),
    }
    assert clinician.post(URL + "services/", {}, format="json").status_code == 403
    officer = api_as("billing_officer", facility=facility)
    response = officer.post(
        URL + f"price-lists/{lists['cash'].pk}/prices/",
        {"service": str(fbc.pk), "price": "820.00", "reason": "Review"},
        format="json",
    )
    assert response.status_code == 202
    assert (
        ApprovalRequest.objects.get(pk=response.json()["approval_id"]).action == "billing.price.set"
    )
    items = officer.get(URL + f"price-lists/{lists['cash'].pk}/items/").json()
    assert items[0]["price"] == "800.00"
    patch = officer.patch(
        URL + f"services/{fbc.pk}/", {"sha_interventions": ["SYN-1"]}, format="json"
    )
    assert patch.json()["sha_interventions"] == ["SYN-1"]
    assert officer.patch(URL + f"services/{fbc.pk}/", {"code": "X"}, format="json").json()[
        "sha_interventions"
    ] == ["SYN-1"]  # code is not editable: ignored by the serializer


def test_seed_is_idempotent(db):
    from apps.facilities import seed as facility_seed

    out = StringIO()
    command = type("C", (), {"stdout": out})()
    facility_seed.run(command)
    payers_and_schemes()
    seed.run(command)
    seed.run(command)
    site = facility_seed.facility()
    assert Service.objects.filter(facility=site).count() == len(seed.CATALOGUE)
    assert PriceList.objects.filter(facility=site).count() == 3
    cons = Service.objects.get(facility=site, code="CONS-GEN")
    assert services.resolve_price(cons).amount == Decimal("500.00")
    assert all(
        code.startswith("SYN-SHA-") for s in Service.objects.all() for code in s.sha_interventions
    )


def test_service_validation_branches(facility, staff):
    from apps.facilities.tests.factories import DepartmentFactory

    with pytest.raises(ValidationError):
        services._create_service(
            facility=facility, actor=None, code="X1", name="x", kind="lab", sha_interventions="nope"
        )
    with pytest.raises(ValidationError):
        services._create_service(
            facility=facility,
            actor=None,
            code="X2",
            name="x",
            kind="lab",
            department=DepartmentFactory.create(),
        )
    with pytest.raises(ValidationError):
        services._create_service(facility=facility, actor=None, code=" ", name="x", kind="lab")
    officer = staff("billing_officer")
    with pytest.raises(ValidationError):
        services.request_new_service(
            facility=facility, actor=officer, reason="x", code="", name="", kind="lab"
        )
    services._create_service(facility=facility, actor=None, code="DUP", name="x", kind="lab")
    with pytest.raises(ValidationError, match="already exists"):
        services.request_new_service(
            facility=facility, actor=officer, reason="x", code="dup", name="x", kind="lab"
        )


def test_service_status_and_field_rules(facility, fbc, staff):
    officer = staff("billing_officer")
    with pytest.raises(ValidationError):
        services.update_service(fbc, actor=officer, changes={"code": "NEW"})
    with pytest.raises(ValidationError):
        services.set_service_status(fbc, actor=officer, active=False, reason=" ")
    off = services.set_service_status(
        fbc, actor=officer, active=False, reason="Reagent out of stock"
    )
    assert off.status == "inactive" and not off.active
    assert (
        services.set_service_status(off, actor=officer, active=False, reason="again").status
        == "inactive"
    )
    with pytest.raises(PermissionDenied):
        services.set_service_status(fbc, actor=staff("cashier"), active=True, reason="x")
    assert AuditEvent.objects.filter(action="billing.service.status_changed").count() == 1


def test_price_rules_and_missing_cash_list(facility, lists, fbc, staff):
    with pytest.raises(ValidationError):
        price(lists["cash"], fbc, "-1", timezone.localdate())
    other_facility_service = services._create_service(
        facility=__import__(
            "apps.facilities.tests.factories", fromlist=["FacilityFactory"]
        ).FacilityFactory.create(),
        actor=None,
        code="OTHER",
        name="x",
        kind="lab",
    )
    with pytest.raises(ValidationError, match="different facilities"):
        price(lists["cash"], other_facility_service, "1", timezone.localdate())
    officer = staff("billing_officer")
    with pytest.raises(ValidationError):
        services.request_price_change(
            price_list=lists["cash"],
            service=fbc,
            price="-5",
            effective_from=None,
            actor=officer,
            reason="x",
        )
    lists["shif"].active = False
    lists["shif"].save()
    with pytest.raises(ValidationError, match="active price list"):
        services.request_price_change(
            price_list=lists["shif"],
            service=fbc,
            price="5",
            effective_from=None,
            actor=officer,
            reason="x",
        )
    from apps.facilities.tests.factories import FacilityFactory

    with pytest.raises(ValidationError, match="no active cash"):
        services.cash_list(FacilityFactory.create())


def test_late_approval_never_backdates_a_price(facility, lists, fbc, staff):
    import time_machine

    price(lists["cash"], fbc, "800.00", timezone.localdate() - timedelta(days=10))
    request = services.request_price_change(
        price_list=lists["cash"],
        service=fbc,
        price="900",
        effective_from=timezone.localdate(),
        actor=staff("billing_officer"),
        reason="x",
    )
    with time_machine.travel(timezone.now() + timedelta(days=2)):
        approvals.approve(request, approver=staff("finance_manager"))
        item = PriceListItem.objects.get(service=fbc, effective_to__isnull=True)
        assert item.effective_from == timezone.localdate()
