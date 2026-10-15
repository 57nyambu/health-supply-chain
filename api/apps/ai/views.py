"""Legacy AI endpoints (off unless AI_FEATURES_ENABLED, ADR-014) and the public non-PHI API.

The AI endpoints send stock and facility statistics (and, for OCR, an uploaded image)
to an external model API. They stay disabled until a DPIA covers them; when enabled
they only see the stores of the request's facility.
"""

from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.access.authentication import ApiKeyAuthentication
from apps.access.drf import request_facility
from apps.audit.services import record
from apps.core.problems import ApiProblem
from apps.warehouses.selectors import facility_warehouses

from .gemma_client import GemmaClient, GemmaClientError
from .serializers import AssistantRequestSerializer, OCRIntakeSerializer
from .tools import (
    get_facility_stats,
    get_low_stock_alerts,
    get_transfer_candidates,
    local_forecast,
    public_facility_directory,
    public_facility_stats,
    public_high_severity_alerts,
)


class FeatureDisabled(ApiProblem):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "This feature is turned off."
    default_code = "feature_disabled"


class AIFeatureView(APIView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not settings.AI_FEATURES_ENABLED:
            raise FeatureDisabled()

    def warehouse_ids(self) -> list[int]:
        return list(
            facility_warehouses(request_facility(self.request)).values_list("pk", flat=True)
        )


class AssistantView(AIFeatureView):
    policy = "ai.assistant.use"

    def post(self, request):
        serializer = AssistantRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query = serializer.validated_data["query"].lower()
        warehouses = self.warehouse_ids()
        context: dict = {}
        tools_called = []
        if "stock" in query or "low" in query:
            context["low_stock"] = get_low_stock_alerts(warehouse_ids=warehouses)
            tools_called.append("get_low_stock_alerts")
        if any(word in query for word in ("facility", "attendance", "footfall")):
            context["facility_stats"] = [get_facility_stats(w, days=7) for w in warehouses]
            tools_called.append("get_facility_stats")
        if ("transfer" in query or "redistribution" in query) and context.get("low_stock"):
            context["transfer_candidates"] = get_transfer_candidates(
                context["low_stock"][0]["product_id"], warehouse_ids=warehouses
            )
            tools_called.append("get_transfer_candidates")
        prompt = (
            "You are an assistant for health facility supply coordination. "
            "Answer concisely using only the provided context; say what is missing.\n\n"
            f"User query: {serializer.validated_data['query']}\n\nContext JSON: {context}"
        )
        try:
            answer = GemmaClient().generate_text(prompt) or ""
        except GemmaClientError:
            answer = ""
        record(
            "ai.assistant.used",
            request.user,
            None,
            facility=request_facility(request),
            detail={"tools": tools_called},
        )
        return Response(
            {
                "answer": answer or "AI response is unavailable.",
                "tools_called": tools_called,
                "context": context,
            }
        )


class OCRIntakeView(AIFeatureView):
    policy = "ai.ocr.use"
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = OCRIntakeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prompt = (
            "Extract a JSON object with this schema only: "
            '{"extracted":{"commodity_name":"","quantity":0,"unit":"","date_recorded":"YYYY-MM-DD"},'
            '"confidence_note":"", "requires_confirmation": true}.'
        )
        try:
            payload = GemmaClient(model=settings.GEMMA_MODEL_VISION).generate_vision_json(
                serializer.validated_data["image"], prompt
            )
        except GemmaClientError:
            payload = {
                "extracted": {
                    "commodity_name": "Unknown",
                    "quantity": 0,
                    "unit": "units",
                    "date_recorded": "",
                },
                "confidence_note": "Vision model unavailable. Please enter values manually.",
                "requires_confirmation": True,
            }
        record("ai.ocr.used", request.user, None, facility=request_facility(request))
        return Response(payload)


class ForecastView(AIFeatureView):
    policy = "ai.forecast.read"

    def get(self, request, warehouse_id, product_id):
        if warehouse_id not in self.warehouse_ids():
            raise NotFound()
        cache_key = f"ai:forecast:{warehouse_id}:{product_id}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)
        forecast = local_forecast(warehouse_id, product_id)
        if not forecast:
            raise NotFound()
        cache.set(cache_key, forecast, timeout=settings.GEMMA_CACHE_TTL_SECONDS)
        return Response(forecast)


class RedistributionSuggestionsView(AIFeatureView):
    policy = "ai.redistribution.read"

    def get(self, request):
        warehouses = self.warehouse_ids()
        suggestions = []
        seen = set()
        for row in get_low_stock_alerts(warehouse_ids=warehouses, limit=5):
            if row["product_id"] not in seen:
                seen.add(row["product_id"])
                suggestions.extend(
                    get_transfer_candidates(row["product_id"], warehouse_ids=warehouses)
                )
        return Response(suggestions)


class PublicView(APIView):
    """Non-PHI public API for integrators: hashed API keys, service-account role, throttled."""

    authentication_classes = [ApiKeyAuthentication]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_api"
    policy = "public.facility.read"


class PublicFacilitiesView(PublicView):
    def get(self, request):
        return Response(public_facility_directory())


class PublicAlertsView(PublicView):
    def get(self, request):
        return Response(public_high_severity_alerts())


class PublicFacilityStatsView(PublicView):
    def get(self, request, facility_id):
        payload = public_facility_stats(facility_id)
        if not payload:
            raise NotFound()
        return Response(payload)
