"""Pagination conventions (DESIGN §17).

- Large, growing lists (patients, visits, audit, transactions) use cursor
  pagination: stable under inserts, no expensive COUNT, no page-number
  enumeration of sequential data.
- Catalogues (products, services, wards, roles…) use page numbers; this is
  the project default.
"""

from rest_framework.pagination import CursorPagination, PageNumberPagination


class CataloguePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class LargeListCursorPagination(CursorPagination):
    """Newest first. Views over models without ``created_at`` set ``ordering``."""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
    ordering = "-created_at"
