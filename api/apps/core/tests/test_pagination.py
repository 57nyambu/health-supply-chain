import pytest
from django.conf import settings
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny
from rest_framework.test import APIRequestFactory

from apps.accounts.models import User
from apps.core.pagination import CataloguePagination, LargeListCursorPagination

pytestmark = pytest.mark.django_db


class UserRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email"]


class CursorList(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserRowSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    pagination_class = LargeListCursorPagination


class CatalogueList(CursorList):
    pagination_class = CataloguePagination
    queryset = User.objects.order_by("email")


@pytest.fixture
def users():
    for index in range(7):
        User.objects.create_user(email=f"user{index}@example.test")


def test_catalogue_pagination_is_the_default():
    assert (
        settings.REST_FRAMEWORK["DEFAULT_PAGINATION_CLASS"]
        == "apps.core.pagination.CataloguePagination"
    )


def test_page_number_pagination_on_catalogues(users):
    request = APIRequestFactory().get("/", {"page_size": 3, "page": 2})
    body = CatalogueList.as_view()(request).data
    assert body["count"] == 7
    assert [row["email"] for row in body["results"]] == [f"user{i}@example.test" for i in (3, 4, 5)]


def test_cursor_pagination_walks_newest_first_without_counts(users):
    view = CursorList.as_view()
    first = view(APIRequestFactory().get("/", {"page_size": 4})).data
    assert "count" not in first
    assert len(first["results"]) == 4
    cursor = first["next"].split("cursor=")[1].split("&")[0]
    second = view(APIRequestFactory().get("/", {"page_size": 4, "cursor": cursor})).data
    seen = [row["email"] for row in first["results"] + second["results"]]
    assert len(seen) == len(set(seen)) == 7
    assert second["next"] is None


def test_page_size_is_capped():
    assert CataloguePagination.max_page_size == LargeListCursorPagination.max_page_size == 200
