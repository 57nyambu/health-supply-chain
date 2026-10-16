"""Access administration API: roles, role assignments and the approvals inbox."""

from typing import Any, cast

from django.db.models import Q, QuerySet
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response

from apps.access import approvals, breakglass, policies
from apps.access.assignments import grant_role, revoke_assignment
from apps.access.drf import AUTHENTICATED, request_facility, require_facility
from apps.access.models import ApprovalRequest, BreakGlassGrant, Role, RoleAssignment
from apps.accounts.models import User
from apps.audit.services import record
from apps.facilities.models import Department, Ward


class RoleSerializer(serializers.ModelSerializer[Role]):
    permissions: serializers.SlugRelatedField[Any] = serializers.SlugRelatedField(
        slug_field="code", many=True, read_only=True
    )

    class Meta:
        model = Role
        fields = [
            "id",
            "code",
            "name",
            "description",
            "privileged",
            "mfa_required",
            "addon",
            "requires_cosign",
            "chart_baseline",
            "chart_care_team",
            "licence_regulators",
            "permissions",
        ]
        read_only_fields = fields


class AssignmentSerializer(serializers.ModelSerializer[RoleAssignment]):
    role = serializers.SlugRelatedField(
        slug_field="code", queryset=Role.objects.filter(active=True)
    )
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True))
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), required=False, allow_null=True
    )
    ward = serializers.PrimaryKeyRelatedField(
        queryset=Ward.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = RoleAssignment
        fields = [
            "id",
            "user",
            "role",
            "department",
            "ward",
            "valid_from",
            "valid_to",
            "status",
            "reason",
            "granted_by",
            "approved_by",
            "approval",
            "revoked_at",
        ]
        read_only_fields = ["id", "status", "granted_by", "approved_by", "approval", "revoked_at"]
        extra_kwargs = {"valid_from": {"required": False}, "reason": {"required": True}}


class RevokeSerializer(serializers.Serializer[None]):
    reason = serializers.CharField(max_length=255)


class DecisionSerializer(serializers.Serializer[None]):
    comment = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class ApprovalSerializer(serializers.ModelSerializer[ApprovalRequest]):
    class Meta:
        model = ApprovalRequest
        fields = [
            "id",
            "action",
            "required_permissions",
            "amount",
            "threshold_band",
            "resource_type",
            "resource_id",
            "reason",
            "status",
            "requested_by",
            "requested_at",
            "expires_at",
            "decided_at",
        ]
        read_only_fields = fields


class RoleViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet[Role]):
    serializer_class = RoleSerializer
    queryset = Role.objects.filter(active=True).prefetch_related("permissions").order_by("name")
    pagination_class = None
    policy = "access.role.read"


class AssignmentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet[RoleAssignment],
):
    serializer_class = AssignmentSerializer
    queryset = RoleAssignment.objects.none()
    policy = {
        "list": "access.assignment.read",
        "retrieve": "access.assignment.read",
        "create": "access.assignment.manage",
        "revoke": "access.assignment.manage",
    }

    def get_queryset(self) -> QuerySet[RoleAssignment]:
        queryset = RoleAssignment.objects.filter(
            facility_id=require_facility(self.request)
        ).select_related("role")
        user = self.request.query_params.get("user")
        return queryset.filter(user_id=user) if user else queryset

    def perform_create(self, serializer: Any) -> None:
        data = dict(serializer.validated_data)
        serializer.instance = grant_role(
            granted_by=self.request.user,
            user=data["user"],
            role=data["role"],
            facility=require_facility(self.request),
            reason=data.get("reason", ""),
            department=data.get("department"),
            ward=data.get("ward"),
            valid_from=data.get("valid_from"),
            valid_to=data.get("valid_to"),
        )

    @action(detail=True, methods=["post"], serializer_class=RevokeSerializer)
    def revoke(self, request: Request, pk: str | None = None) -> Response:
        serializer = RevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = revoke_assignment(
            self.get_object(), revoked_by=request.user, reason=serializer.validated_data["reason"]
        )
        return Response(AssignmentSerializer(assignment).data)


class ApprovalViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet[ApprovalRequest]
):
    """Requests the user made, or may decide, in the request facility (services enforce rights)."""

    serializer_class = ApprovalSerializer
    queryset = ApprovalRequest.objects.none()
    policy = AUTHENTICATED

    def get_queryset(self) -> QuerySet[ApprovalRequest]:
        facility_id = request_facility(self.request)
        if facility_id is None:
            return ApprovalRequest.objects.none()
        mine = policies.effective_permissions(self.request.user, facility=facility_id)
        decidable = Q()
        for code in mine:
            decidable |= Q(required_permissions__contains=[code])
        queryset = ApprovalRequest.objects.filter(facility_id=facility_id).filter(
            Q(requested_by=self.request.user) | (decidable if mine else Q(pk__in=[]))
        )
        wanted = self.request.query_params.get("status")
        return queryset.filter(status=wanted) if wanted else queryset

    def facility_of(self, obj: ApprovalRequest) -> int:
        return obj.facility_id

    @action(detail=True, methods=["post"], serializer_class=DecisionSerializer)
    def approve(self, request: Request, pk: str | None = None) -> Response:
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decided = approvals.approve(
            self.get_object(), approver=request.user, comment=serializer.validated_data["comment"]
        )
        return Response(ApprovalSerializer(decided).data)

    @action(detail=True, methods=["post"], serializer_class=DecisionSerializer)
    def reject(self, request: Request, pk: str | None = None) -> Response:
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decided = approvals.reject(
            self.get_object(), approver=request.user, comment=serializer.validated_data["comment"]
        )
        return Response(ApprovalSerializer(decided).data, status=status.HTTP_200_OK)


class BreakGlassSerializer(serializers.ModelSerializer[BreakGlassGrant]):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = BreakGlassGrant
        fields = [
            "id",
            "user",
            "user_name",
            "patient",
            "reason",
            "justification",
            "granted_at",
            "expires_at",
            "ended_at",
            "review_status",
            "reviewed_by",
            "reviewed_at",
            "review_note",
        ]
        read_only_fields = fields

    def get_user_name(self, obj: BreakGlassGrant) -> str:
        return obj.user.get_full_name() or obj.user.email


class BreakGlassEndedSerializer(serializers.ModelSerializer[BreakGlassGrant]):
    class Meta:
        model = BreakGlassGrant
        fields = ["id", "ended_at"]
        read_only_fields = fields


class BreakGlassReviewSerializer(serializers.Serializer[None]):
    outcome = serializers.ChoiceField(
        choices=[BreakGlassGrant.Review.JUSTIFIED, BreakGlassGrant.Review.ESCALATED]
    )
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class BreakGlassViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet[BreakGlassGrant]
):
    """The break-glass review queue (medical superintendent, DPO); viewing it is audited."""

    serializer_class = BreakGlassSerializer
    queryset = BreakGlassGrant.objects.none()
    policy = {
        "list": "access.breakglass.review",
        "retrieve": "access.breakglass.review",
        "review": "access.breakglass.review",
        "end": "access.breakglass.request",
    }

    def get_queryset(self) -> QuerySet[BreakGlassGrant]:
        queryset = BreakGlassGrant.objects.filter(
            facility_id=require_facility(self.request)
        ).select_related("user")
        wanted = self.request.query_params.get("review_status")
        return queryset.filter(review_status=wanted) if wanted else queryset

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        response = super().list(request, *args, **kwargs)
        record(
            "access.breakglass.queue_viewed",
            request.user,
            facility=require_facility(request),
            purpose="audit",
        )
        return response

    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        grant = self.get_object()
        record(
            "access.breakglass.viewed",
            request.user,
            grant,
            patient=grant.patient_id,
            purpose="audit",
        )
        return Response(BreakGlassSerializer(grant).data)

    @action(detail=True, methods=["post"], serializer_class=BreakGlassReviewSerializer)
    def review(self, request: Request, pk: str | None = None) -> Response:
        serializer = BreakGlassReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        grant = breakglass.review(
            self.get_object(), reviewer=request.user, **serializer.validated_data
        )
        return Response(BreakGlassSerializer(grant).data)

    @action(detail=True, methods=["post"], serializer_class=BreakGlassEndedSerializer)
    def end(self, request: Request, pk: str | None = None) -> Response:
        """The clinician leaves emergency access early (their own grant only)."""
        grant = BreakGlassGrant.objects.filter(
            pk=str(pk), facility_id=require_facility(request), user=cast(Any, request.user)
        ).first()
        if grant is None:
            raise NotFound()
        grant = breakglass.end_access(grant, user=request.user)
        return Response(BreakGlassEndedSerializer(grant).data)
