"""Visits, queues, gates and boards API (P2-VIS-01..03): thin views over visits.services."""

from datetime import timedelta
from typing import Any, cast

from django.db.models import Count, Q, QuerySet
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.authentication import BaseAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, NotFound, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.authentication import ServicePrincipal
from apps.access.drf import require_facility
from apps.access.roles import ChartAccess
from apps.audit.services import record
from apps.core.pagination import LargeListCursorPagination
from apps.facilities.models import ServicePoint
from apps.insurance.models import Coverage
from apps.patients import selectors as patient_selectors
from apps.patients.models import Patient
from apps.visits import gates, services
from apps.visits.models import GatePolicy, QueueBoard, QueueTicket, Visit

from .serializers import (
    ApprovalRefSerializer,
    BoardCreatedSerializer,
    BoardCreateSerializer,
    BoardDisplaySerializer,
    BoardSerializer,
    CallSerializer,
    DispositionSerializer,
    GateDecisionSerializer,
    GateOverrideRequestSerializer,
    GateOverrideSerializer,
    GatePolicyChangeSerializer,
    GatePolicySerializer,
    GateQuerySerializer,
    PrioritiseSerializer,
    ServicePointQueueSerializer,
    TicketSerializer,
    TransferSerializer,
    VisitDetailSerializer,
    VisitOpenSerializer,
    VisitQuerySerializer,
    VisitSerializer,
    VisitTransitionSerializer,
)

READ = "visits.visit.read"
QUEUE = "visits.queue.manage"


def _point(facility_id: int, point_id: Any) -> ServicePoint:
    point = ServicePoint.objects.filter(pk=point_id, facility_id=facility_id, active=True).first()
    if point is None:
        raise ValidationError({"service_point": "Choose an active service point of this facility."})
    return point


class VisitViewSet(mixins.ListModelMixin, viewsets.GenericViewSet[Visit]):
    serializer_class = VisitSerializer
    queryset = Visit.objects.none()
    pagination_class = LargeListCursorPagination
    policy = {
        "list": READ,
        "retrieve": READ,
        "create": "visits.visit.create",
        "transition": READ,  # the target status decides the permission (services.TARGET_PERMISSION)
        "disposition": "clinical.note.write",
        "gate": READ,
        "override_gate": "visits.gate.override",
    }

    def get_queryset(self) -> QuerySet[Visit]:
        return (
            Visit.objects.filter(facility_id=require_facility(self.request))
            .select_related("patient", "coverage__scheme")
            .order_by("-opened_at")
        )

    def get_object(self) -> Visit:
        visit = self.get_queryset().filter(pk=self.kwargs["pk"]).first()
        if visit is None:
            raise NotFound()
        return visit

    @extend_schema(parameters=[VisitQuerySerializer], responses=VisitSerializer(many=True))
    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        query = VisitQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        rows = self.get_queryset()
        if data.get("status"):
            rows = rows.filter(status__in=list(data["status"]))
        if data.get("visit_type"):
            rows = rows.filter(visit_type=data["visit_type"])
        if data.get("patient"):
            rows = rows.filter(patient_id=data["patient"])
        if data.get("open") is True:
            rows = rows.exclude(status__in=list(services.NOT_OPEN))
        if data.get("date"):
            rows = rows.filter(opened_at__date=data["date"])
        page = self.paginate_queryset(rows)
        items = page if page is not None else list(rows)
        record(
            "visits.visit.listed",
            request.user,
            facility=require_facility(request),
            detail={"count": len(items)},
        )
        body = VisitSerializer(items, many=True).data
        return self.get_paginated_response(body) if page is not None else Response(body)

    @extend_schema(
        parameters=[OpenApiParameter("purpose", str, enum=["care", "registration", "billing"])],
        responses=VisitDetailSerializer,
    )
    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        visit = self.get_object()
        patient_selectors.open_record(
            request.user,
            visit.patient,
            purpose=request.query_params.get("purpose", "care"),
            needed=ChartAccess.DEMOGRAPHICS,
            action="visits.visit.viewed",
        )
        return Response(VisitDetailSerializer(visit).data)

    @extend_schema(request=VisitOpenSerializer, responses={201: VisitSerializer})
    def create(self, request: Request) -> Response:
        serializer = VisitOpenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        facility_id = require_facility(request)
        patient = Patient.objects.filter(pk=data["patient"], facility_id=facility_id).first()
        if patient is None:
            raise ValidationError({"patient": "Choose a patient of this facility."})
        coverage = None
        if data["coverage"]:
            coverage = Coverage.objects.filter(pk=data["coverage"], patient=patient).first()
            if coverage is None:
                raise ValidationError({"coverage": "Choose cover of this patient."})
        point = _point(facility_id, data["service_point"]) if data["service_point"] else None
        visit = services.open_visit(
            patient=patient,
            visit_type=data["visit_type"],
            actor=request.user,
            coverage=coverage,
            waiver=data["waiver"],
            service_point=point,
            arrival_mode=data["arrival_mode"],
            brought_by=data["brought_by"],
        )
        return Response(VisitSerializer(visit).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=VisitTransitionSerializer, responses=VisitSerializer)
    @action(detail=True, methods=["post"])
    def transition(self, request: Request, pk: str | None = None) -> Response:
        serializer = VisitTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        visit = services.transition(
            self.get_object(),
            data["to"],
            actor=request.user,
            reason=data["reason"],
            check_permission=True,
            expected_version=data["version"],
        )
        return Response(VisitSerializer(visit).data)

    @extend_schema(request=DispositionSerializer, responses=VisitSerializer)
    @action(detail=True, methods=["post"])
    def disposition(self, request: Request, pk: str | None = None) -> Response:
        serializer = DispositionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        visit = services.record_disposition(
            self.get_object(), serializer.validated_data["disposition"], actor=request.user
        )
        return Response(VisitSerializer(visit).data)

    @extend_schema(parameters=[GateQuerySerializer], responses=GateDecisionSerializer)
    @action(detail=True, methods=["get"])
    def gate(self, request: Request, pk: str | None = None) -> Response:
        query = GateQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        decision = gates.evaluate(self.get_object(), query.validated_data["context"])
        return Response(GateDecisionSerializer(decision).data)

    @extend_schema(request=GateOverrideRequestSerializer, responses={201: GateOverrideSerializer})
    @action(detail=True, methods=["post"], url_path="gate-override")
    def override_gate(self, request: Request, pk: str | None = None) -> Response:
        serializer = GateOverrideRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = gates.override(self.get_object(), actor=request.user, **serializer.validated_data)
        return Response(GateOverrideSerializer(row).data, status=status.HTTP_201_CREATED)


class QueueViewSet(viewsets.GenericViewSet[ServicePoint]):
    """Queues per service point: counts, the ordered list and call-next."""

    queryset = ServicePoint.objects.none()
    serializer_class = ServicePointQueueSerializer
    pagination_class = None
    policy = {"list": READ, "retrieve": READ, "call_next": QUEUE}

    def get_queryset(self) -> QuerySet[ServicePoint]:
        return ServicePoint.objects.filter(facility_id=require_facility(self.request), active=True)

    @extend_schema(responses=ServicePointQueueSerializer(many=True))
    def list(self, request: Request) -> Response:
        today = timezone.localdate()
        active = Q(tickets__service_date__gte=today - timedelta(days=1))
        rows = self.get_queryset().annotate(
            waiting=Count("tickets", filter=active & Q(tickets__status="waiting")),
            called=Count("tickets", filter=active & Q(tickets__status="called")),
            serving=Count("tickets", filter=active & Q(tickets__status="serving")),
        )
        return Response(ServicePointQueueSerializer(rows.order_by("kind", "code"), many=True).data)

    @extend_schema(responses=TicketSerializer(many=True))
    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        """Called and serving tickets first, then waiting tickets in queue order."""
        point = _point(require_facility(request), pk)
        live = QueueTicket.objects.filter(
            service_point=point, status__in=[QueueTicket.Status.CALLED, QueueTicket.Status.SERVING]
        ).select_related("visit__patient", "visit__coverage__scheme", "service_point")
        tickets = sorted(live, key=lambda t: t.called_at or t.arrived_at) + [
            t
            for t in services.ordered(
                QueueTicket.objects.filter(
                    service_point=point, status=QueueTicket.Status.WAITING
                ).select_related("visit__patient", "visit__coverage__scheme", "service_point")
            )
        ]
        record(
            "visits.queue.viewed",
            request.user,
            facility=point.facility_id,
            detail={"service_point": point.code, "count": len(tickets)},
        )
        return Response(TicketSerializer(tickets, many=True).data)

    @extend_schema(request=CallSerializer, responses={200: TicketSerializer, 204: None})
    @action(detail=True, methods=["post"], url_path="call-next")
    def call_next(self, request: Request, pk: str | None = None) -> Response:
        serializer = CallSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = services.call_next(
            _point(require_facility(request), pk), actor=request.user, **serializer.validated_data
        )
        if ticket is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(TicketSerializer(ticket).data)


class TicketViewSet(mixins.ListModelMixin, viewsets.GenericViewSet[QueueTicket]):
    """Ticket actions. ``GET ?lwbs=true`` is the left-before-seen work queue."""

    serializer_class = TicketSerializer
    queryset = QueueTicket.objects.none()
    pagination_class = None
    policy = {
        "list": READ,
        "call": QUEUE,
        "start": QUEUE,
        "finish": QUEUE,
        "skip": QUEUE,
        "transfer": QUEUE,
        "send_back": QUEUE,
        "prioritise": QUEUE,
        "confirm_lwbs": QUEUE,
        "dismiss_lwbs": QUEUE,
    }

    def get_queryset(self) -> QuerySet[QueueTicket]:
        return QueueTicket.objects.filter(
            facility_id=require_facility(self.request)
        ).select_related("visit__patient", "visit__coverage__scheme", "service_point")

    def get_object(self) -> QueueTicket:
        ticket = self.get_queryset().filter(pk=self.kwargs["pk"]).first()
        if ticket is None:
            raise NotFound()
        return ticket

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        rows = self.get_queryset()
        if request.query_params.get("lwbs") == "true":
            rows = services.lwbs_work_queue(require_facility(request)).select_related(
                "visit__patient"
            )
        else:
            rows = rows.filter(service_date=timezone.localdate())
        items = list(rows[:500])
        record(
            "visits.queue.viewed",
            request.user,
            facility=require_facility(request),
            detail={"count": len(items), "lwbs": request.query_params.get("lwbs") == "true"},
        )
        return Response(TicketSerializer(items, many=True).data)

    def _done(self, ticket: QueueTicket) -> Response:
        ticket = self.get_queryset().get(pk=ticket.pk)
        return Response(TicketSerializer(ticket).data)

    @extend_schema(request=CallSerializer, responses=TicketSerializer)
    @action(detail=True, methods=["post"])
    def call(self, request: Request, pk: str | None = None) -> Response:
        serializer = CallSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._done(
            services.call(self.get_object(), actor=request.user, **serializer.validated_data)
        )

    @extend_schema(request=None, responses=TicketSerializer)
    @action(detail=True, methods=["post"])
    def start(self, request: Request, pk: str | None = None) -> Response:
        return self._done(services.start_serving(self.get_object(), actor=request.user))

    @extend_schema(request=None, responses=TicketSerializer)
    @action(detail=True, methods=["post"])
    def finish(self, request: Request, pk: str | None = None) -> Response:
        return self._done(services.finish(self.get_object(), actor=request.user))

    @extend_schema(request=None, responses=TicketSerializer)
    @action(detail=True, methods=["post"])
    def skip(self, request: Request, pk: str | None = None) -> Response:
        return self._done(services.skip(self.get_object(), actor=request.user))

    @extend_schema(request=TransferSerializer, responses=TicketSerializer)
    @action(detail=True, methods=["post"])
    def transfer(self, request: Request, pk: str | None = None) -> Response:
        return self._move(request, send_back=False)

    @extend_schema(request=TransferSerializer, responses=TicketSerializer)
    @action(detail=True, methods=["post"], url_path="send-back")
    def send_back(self, request: Request, pk: str | None = None) -> Response:
        return self._move(request, send_back=True)

    def _move(self, request: Request, *, send_back: bool) -> Response:
        serializer = TransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        ticket = self.get_object()
        new = services.transfer(
            ticket,
            _point(ticket.facility_id, data["service_point"]),
            actor=request.user,
            note=data["note"],
            send_back=send_back,
        )
        return self._done(new)

    @extend_schema(request=PrioritiseSerializer, responses=TicketSerializer)
    @action(detail=True, methods=["post"])
    def prioritise(self, request: Request, pk: str | None = None) -> Response:
        serializer = PrioritiseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._done(
            services.prioritise(self.get_object(), actor=request.user, **serializer.validated_data)
        )

    @extend_schema(request=None, responses=VisitSerializer)
    @action(detail=True, methods=["post"], url_path="confirm-lwbs")
    def confirm_lwbs(self, request: Request, pk: str | None = None) -> Response:
        visit = services.confirm_left_before_seen(self.get_object(), actor=request.user)
        return Response(VisitSerializer(visit).data)

    @extend_schema(request=None, responses=TicketSerializer)
    @action(detail=True, methods=["post"], url_path="dismiss-lwbs")
    def dismiss_lwbs(self, request: Request, pk: str | None = None) -> Response:
        return self._done(services.dismiss_left_before_seen(self.get_object(), actor=request.user))


class GatePolicyViewSet(mixins.ListModelMixin, viewsets.GenericViewSet[GatePolicy]):
    serializer_class = GatePolicySerializer
    queryset = GatePolicy.objects.none()
    pagination_class = None
    policy = {"list": "visits.gate.manage", "create": "visits.gate.manage"}

    def get_queryset(self) -> QuerySet[GatePolicy]:
        return GatePolicy.objects.filter(facility_id=require_facility(self.request))

    @extend_schema(request=GatePolicyChangeSerializer, responses={202: ApprovalRefSerializer})
    def create(self, request: Request) -> Response:
        """Ask a second administrator to approve a gate change (maker-checker)."""
        serializer = GatePolicyChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        approval = gates.request_policy_change(
            facility=require_facility(request), actor=request.user, **serializer.validated_data
        )
        return Response(
            ApprovalRefSerializer({"approval_id": approval.pk, "status": approval.status}).data,
            status=status.HTTP_202_ACCEPTED,
        )


class BoardViewSet(mixins.ListModelMixin, viewsets.GenericViewSet[QueueBoard]):
    serializer_class = BoardSerializer
    queryset = QueueBoard.objects.none()
    pagination_class = None
    policy = {
        "list": "visits.board.manage",
        "create": "visits.board.manage",
        "revoke": "visits.board.manage",
    }

    def get_queryset(self) -> QuerySet[QueueBoard]:
        return QueueBoard.objects.filter(
            facility_id=require_facility(self.request)
        ).prefetch_related("service_points")

    @extend_schema(request=BoardCreateSerializer, responses={201: BoardCreatedSerializer})
    def create(self, request: Request) -> Response:
        """The device token is returned once; enter it on the TV (``/board#<token>``)."""
        serializer = BoardCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        facility_id = require_facility(request)
        points = list(
            ServicePoint.objects.filter(
                pk__in=serializer.validated_data["service_points"], facility_id=facility_id
            )
        )
        if len(points) != len(set(serializer.validated_data["service_points"])):
            raise ValidationError({"service_points": "Choose service points of this facility."})
        board, token = services.create_board(
            facility=facility_id,
            name=serializer.validated_data["name"],
            service_points=points,
            actor=request.user,
        )
        data = dict(BoardSerializer(board).data)
        data["token"] = token
        return Response(data, status=status.HTTP_201_CREATED)

    @extend_schema(request=None, responses=BoardSerializer)
    @action(detail=True, methods=["post"])
    def revoke(self, request: Request, pk: str | None = None) -> Response:
        board = self.get_queryset().filter(pk=str(pk)).first()
        if board is None:
            raise NotFound()
        return Response(BoardSerializer(services.revoke_board(board, actor=request.user)).data)


class BoardPrincipal(ServicePrincipal):
    """``request.user`` for a queue board: may show its own board and nothing else."""

    def __init__(self, board: QueueBoard) -> None:
        self.board = board
        self._codes = {"visits.board.display"}

    def __str__(self) -> str:
        return f"queue-board:{self.board.pk}"


class BoardTokenAuthentication(BaseAuthentication):
    HEADER = "X-Board-Token"

    def authenticate(self, request: Request) -> tuple[Any, Any] | None:
        token = request.headers.get(self.HEADER)
        if not token:
            return None
        board = services.board_for_token(token)
        if board is None:
            raise AuthenticationFailed("This board is not recognised; ask an administrator.")
        return BoardPrincipal(board), board

    def authenticate_header(self, request: Request) -> str:
        return self.HEADER


class BoardDisplayView(APIView):
    """What the TV shows: called tickets and the next waiting numbers. No names (KE-DPA-01)."""

    authentication_classes = [BoardTokenAuthentication]
    policy = "visits.board.display"

    @extend_schema(responses=BoardDisplaySerializer)
    def get(self, request: Request) -> Response:
        board = cast(QueueBoard, request.auth)
        today = timezone.localdate()
        points = list(board.service_points.filter(active=True))
        tickets = QueueTicket.objects.filter(
            service_point__in=points, service_date=today
        ).select_related("service_point", "visit")
        calling = sorted(
            (t for t in tickets if t.status == QueueTicket.Status.CALLED),
            key=lambda t: t.called_at or t.arrived_at,
            reverse=True,
        )

        def row(t: QueueTicket) -> dict[str, Any]:
            return {
                "number": t.number,
                "room": t.room or t.service_point.name,
                "service_point": t.service_point.name,
                "status": t.status,
                "called_at": t.called_at,
            }

        waiting = services.ordered([t for t in tickets if t.status == QueueTicket.Status.WAITING])
        QueueBoard.objects.filter(pk=board.pk).update(last_seen_at=timezone.now())
        body = {
            "name": board.name,
            "now_calling": [row(t) for t in calling[:8]],
            "waiting": [row(t) for t in waiting[:20]],
        }
        response = Response(BoardDisplaySerializer(body).data)
        response["Cache-Control"] = "no-store"
        return response
