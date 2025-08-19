from django.core.cache import cache
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Categories
from .serializers import CategoriesSerializer

from rest_framework.permissions import IsAuthenticated, AllowAny

class CategoriesListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        cache_key = "categories_list"
        data = cache.get(cache_key)

        if not data:
            queryset = Categories.objects.filter(is_active=True)
            serializer = CategoriesSerializer(queryset, many=True)
            data = serializer.data
            cache.set(cache_key, data, timeout=60*5)  # cache for 5 mins

        return Response(data)
