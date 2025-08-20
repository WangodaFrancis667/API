from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.response import Response
from .models import Categories, Products, ProductMetaData
from .serializers import CategoriesSerializer, ProductsSerializer, ProductMetaDataSerializer

from rest_framework.permissions import IsAuthenticated, AllowAny

# class CategoriesListView(APIView):
#     permission_classes = [AllowAny]
#     def get(self, request):
#         cache_key = "categories_list"
#         data = cache.get(cache_key)

#         if not data:
#             queryset = Categories.objects.filter(is_active=True)
#             serializer = CategoriesSerializer(queryset, many=True)
#             data = serializer.data
#             cache.set(cache_key, data, timeout=60*5)  # cache for 5 mins

#         return Response(data)



class CategoriesListView(generics.ListAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # Try Redis cache first
        data = cache.get("categories_list")
        if data is not None:
            return Response({"source": "cache", "data": data})

        try:
            # If cache miss or Redis down, fetch from DB
            queryset = Categories.objects.filter(is_active=True)
            serializer = CategoriesSerializer(queryset, many=True)
            data = serializer.data

            # Save into cache (in case Redis comes back)
            cache.set("categories_list", data, timeout=60*10)

            return Response({"source": "db", "data": data})
        except Exception as e:
            # Final fallback — if DB also fails
            return Response(
                {"error": "Service unavailable. Please try again later.", "details": str(e)},
                status=503
            )


# class ProductView(generics.ListCreateAPIView):
#     permission_classes = [AllowAny]
#     serializer_class = ProductsSerializer

#     def get_queryset(self):
#         return Products.objects.filter(is_active=True)

#     def list(self, request, *args, **kwargs):
#         # Try Redis cache first
#         data = cache.get("products_list")
#         if data is not None:
#             return Response({"source": "cache", "data": data})

#         try:
#             # If cache miss or Redis down, fetch from DB
#             queryset = self.get_queryset()
#             serializer = self.get_serializer(queryset, many=True)
#             data = serializer.data

#             # Save into cache (in case Redis comes back)
#             cache.set("products_list", data, timeout=60*10)

#             return Response({"source": "db", "data": data})
#         except Exception as e:
#             # Final fallback — if DB also fails
#             return Response(
#                 {"error": "Service unavailable. Please try again later.", "details": str(e)},
#                 status=503
#             )

#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         self.perform_create(serializer)
#         # Invalidate cache after creation
#         cache.delete("products_list")
#         return Response(serializer.data, status=201)

# for upfate purposes
class ProductFullView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductsSerializer

    def get_queryset(self):
        return Products.objects.filter(is_active=True).order_by("-created_at")

    def list(self, request, *args, **kwargs):
        cache_key = "products_list"

        # Try Redis cache first
        data = cache.get(cache_key)
        if data is not None:
            return Response({"source": "cache", "data": data})

        try:
            # If cache miss, fetch from DB
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data

            # Save into cache
            cache.set(cache_key, data, timeout=60 * 10)  # 10 min cache

            return Response({"source": "db", "data": data})
        except Exception as e:
            # Fallback if DB fails
            return Response(
                {"error": "Service unavailable. Please try again later.", "details": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Invalidate cache so new product shows up immediately
        cache.delete("products_list")

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        instance = serializer.save()
        # Invalidate cache after update
        cache.delete("products_list")
        return instance

    def perform_destroy(self, instance):
        instance.delete()
        # Invalidate cache after delete
        cache.delete("products_list")


class ProductView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductsSerializer

    def get_queryset(self):
        return Products.objects.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        data = cache.get("products_list")
        if data is not None:
            return Response({"source": "cache", "data": data})

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data
        cache.set("products_list", data, timeout=60*10)
        return Response({"source": "db", "data": data})

class ProductDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductsSerializer
    queryset = Products.objects.filter(is_active=True) # (is_active=True)
    lookup_field = "id"

    def retrieve(self, request, *args, **kwargs):
        product_id = kwargs.get("id")
        cache_key = f"product_{product_id}"

        # Try Redis first
        data = cache.get(cache_key)
        if data is not None:
            return Response({"source": "cache", "data": data})

        # Fallback to DB
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        cache.set(cache_key, data, timeout=60*10)
        return Response({"source": "db", "data": data})


# from django.core.cache import cache
# data = cache.get("products_list")
# if data:
#     return Response(data)  # from Redis (super fast)


# Product metat data
class ProductMetaDataView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductMetaDataSerializer

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        return ProductMetaData.objects.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        data = cache.get("products_list")
        if data is not None:
            return Response({"source": "cache", "data": data})

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data
        # cache.set("products_list", data, timeout=60*10)
        return Response({"source": "db", "data": data})