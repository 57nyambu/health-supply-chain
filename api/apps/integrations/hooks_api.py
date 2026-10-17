"""``/api/v1/hooks/<provider>/<token>/`` — inbound callbacks and IPNs (``webhooks``).

Public by design (providers do not hold sessions): each provider's ``verify`` checks the
signature, credentials or secret path token; nothing is processed in the request.
"""

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.drf import PUBLIC
from apps.integrations import webhooks


class HookView(APIView):
    policy = PUBLIC
    authentication_classes: list = []  # no session, so no CSRF; verification is per provider
    mfa_exempt = True

    @extend_schema(request=None, responses={200: None, 403: None, 404: None})
    def post(self, request: Request, provider: str, token: str) -> Response:
        status_code, _row = webhooks.receive(provider, request, token)
        body = {200: {"status": "accepted"}, 403: {"code": "webhook_rejected"}}.get(
            status_code, {"code": "not_found"}
        )
        return Response(body, status=status_code)
