"""Test-only URLconf: the real routes plus probe views for cross-cutting behaviour."""

from django.urls import include, path
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.urls import handler404, handler500  # noqa: F401 - re-exported for the test URLconf

CALLS = {"count": 0}


class ProbeSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=5)
    category = serializers.ChoiceField(choices=["a", "b"])
    when = serializers.DateField()


class ValidationProbe(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        ProbeSerializer(data=request.data).is_valid(raise_exception=True)
        return Response({"ok": True})


class CrashProbe(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        raise RuntimeError("boom with secret context")


class CountingProbe(APIView):
    """Returns how many times it ran; used to prove single execution per key."""

    permission_classes = [AllowAny]
    authentication_classes = []
    idempotency_required = False

    def post(self, request):
        CALLS["count"] += 1
        status_code = int(request.data.get("status", 201))
        return Response(
            {"calls": CALLS["count"], "echo": request.data.get("amount")}, status=status_code
        )


class RequiredKeyProbe(CountingProbe):
    idempotency_required = True


urlpatterns = [
    path("api/test/validation/", ValidationProbe.as_view()),
    path("api/test/crash/", CrashProbe.as_view()),
    path("api/test/counting/", CountingProbe.as_view()),
    path("api/test/required-key/", RequiredKeyProbe.as_view()),
    path("", include("config.urls")),
]
