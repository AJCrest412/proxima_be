from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class CustomPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    page_size = 10

    def get_paginated_response(self, data):
        return Response({
            "total_count": self.page.paginator.count,
            "results": data
        })