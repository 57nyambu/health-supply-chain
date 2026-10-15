from datetime import timedelta
from decimal import Decimal

import pytest
import time_machine
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.access import approvals
from apps.access.models import ApprovalRequest
from apps.audit.models import AuditEvent

pytestmark = pytest.mark.django_db

EXECUTED: list[dict[str, str]] = []


@pytest.fixture(autouse=True)
def executor():
    EXECUTED.clear()
    approvals.register_executor(
        "test.refund", lambda request, approver: EXECUTED.append(request.payload)
    )
    yield
    approvals._executors.pop("test.refund", None)


@pytest.fixture
def people(make_user, facility, grant):
    cashier, manager, other_manager, superintendent = (make_user() for _ in range(4))
    grant(cashier, "cashier", facility)
    grant(manager, "finance_manager", facility)
    grant(other_manager, "finance_manager", facility)
    grant(superintendent, "medical_superintendent", facility)
    return {"cashier": cashier, "manager": manager, "other": other_manager, "supt": superintendent}


def make_request(people, facility, permissions=("payments.refund.approve",), **kw):
    return approvals.request_approval(
        action="test.refund",
        facility=facility,
        requested_by=kw.pop("requested_by", people["cashier"]),
        payload={"payment": "P-1", "amount": "1500.00"},
        required_permissions=list(permissions),
        reason="Duplicate M-Pesa payment",
        amount=Decimal("1500.00"),
        threshold_band="any",
        **kw,
    )


def test_approval_runs_the_executor_once_and_is_audited(people, facility):
    request = make_request(people, facility)
    assert request.payload_hash == approvals.payload_hash(request.payload)
    approvals.approve(request, approver=people["manager"], comment="ok")
    request.refresh_from_db()
    assert request.status == ApprovalRequest.Status.APPROVED
    assert EXECUTED == [{"payment": "P-1", "amount": "1500.00"}]
    actions = list(AuditEvent.objects.order_by("seq").values_list("action", flat=True))
    assert actions == [
        "access.approval.requested",
        "access.approval.approved",
        "access.approval.executed",
    ]


def test_requester_can_never_approve_own_request(people, facility, grant):
    grant(people["cashier"], "finance_manager", facility)  # even holding the approver role
    request = make_request(people, facility)
    with pytest.raises(PermissionDenied, match="own request"):
        approvals.approve(request, approver=people["cashier"])
    assert EXECUTED == []


def test_approver_needs_the_permission_in_that_facility(people, facility, make_user, grant):
    from apps.facilities.tests.factories import FacilityFactory

    elsewhere = make_user()
    grant(elsewhere, "finance_manager", FacilityFactory.create())
    request = make_request(people, facility)
    with pytest.raises(PermissionDenied, match="approver permission"):
        approvals.approve(request, approver=elsewhere)
    with pytest.raises(PermissionDenied):
        approvals.approve(request, approver=people["supt"])


def test_payload_tampering_invalidates_the_request(people, facility):
    request = make_request(people, facility)
    ApprovalRequest.objects.filter(pk=request.pk).update(
        payload={"payment": "P-1", "amount": "15000.00"}
    )
    with pytest.raises(ValidationError, match="changed"):
        approvals.approve(request, approver=people["manager"])
    request.refresh_from_db()
    assert request.status == ApprovalRequest.Status.INVALIDATED
    assert EXECUTED == []
    assert AuditEvent.objects.filter(action="access.approval.invalidated").exists()


def test_two_approver_thresholds_need_distinct_people(people, facility):
    request = make_request(
        people, facility, permissions=("billing.waiver.approve", "billing.waiver.approve_high")
    )
    approvals.approve(request, approver=people["manager"])
    request.refresh_from_db()
    assert request.status == ApprovalRequest.Status.PENDING and EXECUTED == []
    with pytest.raises(PermissionDenied, match="already decided"):
        approvals.approve(request, approver=people["manager"])
    with pytest.raises(PermissionDenied, match="approver permission"):
        approvals.approve(request, approver=people["other"])  # only holds the filled slot
    approvals.approve(request, approver=people["supt"])
    request.refresh_from_db()
    assert request.status == ApprovalRequest.Status.APPROVED
    assert len(EXECUTED) == 1


def test_rejection_needs_a_reason_and_closes_the_request(people, facility):
    request = make_request(people, facility)
    with pytest.raises(ValidationError):
        approvals.reject(request, approver=people["manager"], comment=" ")
    approvals.reject(request, approver=people["manager"], comment="Not a duplicate")
    request.refresh_from_db()
    assert request.status == ApprovalRequest.Status.REJECTED
    with pytest.raises(ValidationError, match="rejected"):
        approvals.approve(request, approver=people["other"])
    assert AuditEvent.objects.filter(action="access.approval.rejected").exists()


def test_expired_requests_cannot_be_approved(people, facility):
    request = make_request(people, facility, ttl=timedelta(hours=1))
    later = timezone.now() + timedelta(hours=2)
    with time_machine.travel(later), pytest.raises(ValidationError, match="expired"):
        approvals.approve(request, approver=people["manager"])
    request.refresh_from_db()
    assert request.status == ApprovalRequest.Status.EXPIRED
    assert EXECUTED == []


def test_expiry_job_expires_and_audits(people, facility):
    make_request(people, facility, ttl=timedelta(hours=1))
    make_request(people, facility, ttl=timedelta(days=5))
    with time_machine.travel(timezone.now() + timedelta(hours=2)):
        assert approvals.expire_overdue() == 1
        assert approvals.expire_overdue() == 0
    assert AuditEvent.objects.filter(action="access.approval.expired").count() == 1


def test_only_the_requester_cancels(people, facility):
    request = make_request(people, facility)
    with pytest.raises(PermissionDenied):
        approvals.cancel(request, by=people["manager"])
    approvals.cancel(request, by=people["cashier"])
    request.refresh_from_db()
    assert request.status == ApprovalRequest.Status.CANCELLED
    with pytest.raises(ValidationError):
        approvals.cancel(request, by=people["cashier"])


@pytest.mark.parametrize(
    ("kwargs", "field"),
    [
        ({"action": "no.such.action"}, "action"),
        ({"required_permissions": ["no.such.perm"]}, "required_permissions"),
        ({"required_permissions": []}, "required_permissions"),
        ({"reason": "  "}, "reason"),
    ],
)
def test_requests_are_validated(people, facility, kwargs, field):
    values = {
        "action": "test.refund",
        "facility": facility,
        "requested_by": people["cashier"],
        "payload": {},
        "required_permissions": ["payments.refund.approve"],
        "reason": "why",
        **kwargs,
    }
    with pytest.raises(ValidationError) as excinfo:
        approvals.request_approval(**values)
    assert field in excinfo.value.message_dict


def test_executor_failure_rolls_back_the_approval(people, facility):
    def boom(request, approver):
        raise RuntimeError("downstream failed")

    approvals.register_executor("test.boom", boom)
    request = approvals.request_approval(
        action="test.boom",
        facility=facility,
        requested_by=people["cashier"],
        payload={},
        required_permissions=["payments.refund.approve"],
        reason="why",
    )
    with pytest.raises(RuntimeError):
        approvals.approve(request, approver=people["manager"])
    request.refresh_from_db()
    assert request.status == ApprovalRequest.Status.PENDING
    assert not request.decisions.exists()
    approvals._executors.pop("test.boom")


def test_expiry_task_runs():
    from apps.access.tasks import expire_approval_requests

    assert expire_approval_requests() == 0
