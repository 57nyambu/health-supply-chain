from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.authentication import PublicAPIKeyAuth
from apps.core.permissions import user_tier, user_warehouse_id

from .gemma_client import GemmaClient, GemmaClientError
from .permissions import HasPublicAPIKey, IsTier1, IsTier1OrTier2
from .serializers import AssistantRequestSerializer, OCRIntakeSerializer
from .tools import (
    get_facility_stats,
    get_low_stock_alerts,
    get_transfer_candidates,
    get_underperforming_facilities,
    local_forecast,
    public_facility_directory,
    public_facility_stats,
    public_high_severity_alerts,
)


def _tier2_scoped_warehouse(request):
    tier = user_tier(request.user)
    if tier != 2:
        return None

    warehouse_id = user_warehouse_id(request.user)
    if not warehouse_id:
        raise ValidationError('Tier 2 users must be assigned to a warehouse.')
    return warehouse_id


class AssistantView(APIView):
    permission_classes = [IsAuthenticated, IsTier1OrTier2]

    def post(self, request):
        serializer = AssistantRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query = serializer.validated_data['query']

        tier = user_tier(request.user)
        warehouse_scope = _tier2_scoped_warehouse(request) if tier == 2 else None

        query_lower = query.lower()
        context = {}
        tools_called = []

        if 'stock' in query_lower or 'low' in query_lower:
            context['low_stock'] = get_low_stock_alerts(warehouse_id=warehouse_scope)
            tools_called.append('get_low_stock_alerts')

        if 'facility' in query_lower or 'attendance' in query_lower or 'footfall' in query_lower:
            if tier == 2 and warehouse_scope:
                context['facility_stats'] = get_facility_stats(warehouse_scope, days=7)
                tools_called.append('get_facility_stats')

        if 'underperform' in query_lower or 'alert' in query_lower:
            if tier == 1:
                context['underperforming_facilities'] = get_underperforming_facilities()
                tools_called.append('get_underperforming_facilities')

        if 'transfer' in query_lower or 'redistribution' in query_lower:
            if tier == 1:
                low_stock = context.get('low_stock') or get_low_stock_alerts(limit=1)
                if low_stock:
                    context['transfer_candidates'] = get_transfer_candidates(low_stock[0]['product_id'])
                    tools_called.append('get_transfer_candidates')

        if not tools_called:
            tools_called.append('general_reasoning')

        prompt = (
            'You are an assistant for district health supply coordination. '
            'Answer concisely and safely using the provided context. '
            'If data is missing, say what is missing instead of inventing values.\n\n'
            f'User query: {query}\n\n'
            f'Context JSON: {context}'
        )

        try:
            answer = GemmaClient().generate_text(prompt)
            if not answer:
                raise GemmaClientError('Empty response from model')
        except GemmaClientError:
            answer = (
                'AI response is currently unavailable. Use the provided context tables and '
                'retry once GEMMA_API_KEY is configured.'
            )

        return Response({'answer': answer, 'tools_called': tools_called, 'context': context})


class OCRIntakeView(APIView):
    permission_classes = [IsAuthenticated, IsTier1OrTier2]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        _tier2_scoped_warehouse(request)

        serializer = OCRIntakeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image = serializer.validated_data['image']

        prompt = (
            'Extract a JSON object with this schema only: '
            '{"extracted":{"commodity_name":"","quantity":0,"unit":"","date_recorded":"YYYY-MM-DD"},'
            '"confidence_note":"", "requires_confirmation": true}. '
            'If uncertain, keep requires_confirmation true.'
        )

        try:
            payload = GemmaClient(model=settings.GEMMA_MODEL_VISION).generate_vision_json(image, prompt)
        except GemmaClientError:
            payload = {
                'extracted': {
                    'commodity_name': 'Unknown',
                    'quantity': 0,
                    'unit': 'units',
                    'date_recorded': '',
                },
                'confidence_note': 'Vision model unavailable. Please verify and enter values manually.',
                'requires_confirmation': True,
            }

        return Response(payload)


class ForecastView(APIView):
    permission_classes = [IsAuthenticated, IsTier1OrTier2]

    def get(self, request, warehouse_id, product_id):
        tier = user_tier(request.user)
        if tier == 2:
            scoped_warehouse = _tier2_scoped_warehouse(request)
            if scoped_warehouse != warehouse_id:
                raise PermissionDenied('Tier 2 users can only access their own facility forecast.')

        cache_key = f'gemma:forecast:{warehouse_id}:{product_id}'
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        forecast = local_forecast(warehouse_id, product_id)
        if not forecast:
            raise NotFound('No inventory record found for this facility/product.')

        prompt = (
            'Given this forecast data, produce one operational recommendation sentence for district health staff. '
            'Do not change the numbers.\n\n'
            f'{forecast}'
        )

        try:
            recommendation = GemmaClient().generate_text(prompt)
            if recommendation:
                forecast['recommendation'] = recommendation.strip()
        except GemmaClientError:
            pass

        cache.set(cache_key, forecast, timeout=settings.GEMMA_CACHE_TTL_SECONDS)
        return Response(forecast)


class RedistributionSuggestionsView(APIView):
    permission_classes = [IsAuthenticated, IsTier1]

    def get(self, request):
        cache_key = 'gemma:redistribution:suggestions'
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        low_stock = get_low_stock_alerts(limit=5)
        suggestions = []
        seen_product_ids = set()

        for row in low_stock:
            product_id = row['product_id']
            if product_id in seen_product_ids:
                continue
            seen_product_ids.add(product_id)
            suggestions.extend(get_transfer_candidates(product_id))

        cache.set(cache_key, suggestions, timeout=settings.GEMMA_CACHE_TTL_SECONDS)
        return Response(suggestions)


class PublicFacilitiesView(APIView):
    authentication_classes = [PublicAPIKeyAuth]
    permission_classes = [HasPublicAPIKey]

    def get(self, request):
        return Response(public_facility_directory())


class PublicAlertsView(APIView):
    authentication_classes = [PublicAPIKeyAuth]
    permission_classes = [HasPublicAPIKey]

    def get(self, request):
        payload = public_high_severity_alerts()
        return Response(payload)


class PublicFacilityStatsView(APIView):
    authentication_classes = [PublicAPIKeyAuth]
    permission_classes = [HasPublicAPIKey]

    def get(self, request, facility_id):
        payload = public_facility_stats(facility_id)
        if not payload:
            raise NotFound('Facility stats not found for this id.')
        return Response(payload)
