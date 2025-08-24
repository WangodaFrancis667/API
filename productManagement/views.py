import json
import logging

from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_redis import get_redis_connection
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView


from .models import (
    Categories, Products, ProductMetaData, ProductImage
    
)

from .serializers import (
    CategoriesSerializer, ProductsSerializer, 
    ProductMetaDataSerializer, ProductMetaDataListSerializer,
    ProductImageSerializer, ProductImageUploadSerializer,
    ProductWithImagesSerializer, BulkImageUploadSerializer,
)

from accounts.permissions import (
    IsAdmin, IsVendor, IsBuyer, IsAdminOrVendor, IsVerifiedVendor,
    CanManageUsers, CanCreateVendor, IsAccountOwner, IsProfileOwner,
    PreventRoleEscalation, RateLimitPermission, 
)

from accounts.security import (
    log_user_activity, cache_user_permissions, get_cached_user_permissions,
    invalidate_user_cache, check_rate_limit, is_suspicious_activity,
    get_user_dashboard_url
)


logger = logging.getLogger(__name__)
User = get_user_model()


class CategoriesListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategoriesSerializer

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


# Full product view
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

# View for creating the products
class ProductCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrVendor]
    serializer_class = ProductsSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer(self, *args, **kwargs):
        """Override to automatically set the vendor field"""
        serializer_class = self.get_serializer_class()
        kwargs.setdefault('context', self.get_serializer_context())
        
        # If this is for creation (POST), add vendor to the data
        if self.request.method == 'POST' and 'data' in kwargs:
            data = kwargs['data'].copy() if hasattr(kwargs['data'], 'copy') else kwargs['data']
            # Set vendor to current user's ID
            data['vendor'] = self.request.user.id
            kwargs['data'] = data
        
        return serializer_class(*args, **kwargs)


    def perform_create(self, serializer):
        user = self.request.user

        # Additional role check 
        if not user.is_authenticated:
            raise PermissionDenied("Authentication is required to create the products.")
        
        if user.role not in ['admin', 'vendor']:
            raise PermissionDenied("Only admins or vendors can create products")
        
        # Save product with the current user
        product = serializer.save(vendor=user)
            
        # log the user activity
        log_user_activity(
             user, 
            'PRODUCT_CREATION', 
            f"Product '{product.title}' created successfully",
            self.request
        )

        # clear relevant cache after product creation
        self._clear_product_cache()

        logger.info(f"Product '{product.title}' created by user {user.username} (ID: {user.id})")

    def create(self, request, *args, **kwargs):
        try:
            # Validate user permissions before processing
            user = request.user
            if not user.is_authenticated:
                return Response(
                    {"error": "Authentication required"}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            if user.role not in ['admin', 'vendor']:
                return Response(
                    {"error": "Only admins and vendors can create products"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            
            # Handle both regular price and group price validation
            regular_price = request.data.get('regular_price')
            group_price = request.data.get('group_price')
            
            if regular_price and group_price:
                try:
                    regular_price_float = float(regular_price)
                    group_price_float = float(group_price)
                    
                    if group_price_float >= regular_price_float:
                        return Response(
                            {"error": "The group price must be less than the regular price"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                except (ValueError, TypeError):
                    return Response(
                        {"error": "Invalid price format. Please provide valid numbers."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            
            # Process the creation
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            # Return success response
            headers = self.get_success_headers(serializer.data)
            return Response({
                "message": "Product created successfully",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED, headers=headers)
            
        except PermissionDenied as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error creating product: {str(e)}")
            return Response(
                {"error": "Failed to create product", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    def _clear_product_cache(self):
        """Clear product-related cache after creation"""
        try:
            redis_conn = get_redis_connection("default")
            cache_patterns = [
                "products_*",
                "categories_*",
                "productmetadata_*"
            ]
            
            total_cleared = 0
            for pattern in cache_patterns:
                keys = redis_conn.keys(pattern)
                if keys:
                    redis_conn.delete(*keys)
                    total_cleared += len(keys)
            
            logger.info(f"Cleared {total_cleared} cache keys after product creation")
        except Exception as e:
            logger.error(f"Error clearing cache after product creation: {str(e)}")


# Product update view
class ProductUpdateView(generics.UpdateAPIView):
    """Update a specific product (PATCH/PUT)"""
    permission_classes = [IsAuthenticated, IsAdminOrVendor]
    serializer_class = ProductsSerializer
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = 'id'
    
    def get_queryset(self):
        user = self.request.user
        # Admin can update any product, vendors can only update their own products
        if user.role == 'admin':
            return Products.objects.all()
        elif user.role == 'vendor':
            return Products.objects.filter(vendor=user)
        else:
            return Products.objects.none()
    
    def get_object(self):
        """Override to add additional permission checks"""
        instance = super().get_object()
        user = self.request.user
        
        # Additional check: vendors can only update their own products
        if user.role == 'vendor' and instance.vendor != user:
            raise PermissionDenied("You can only update your own products.")
        
        return instance
    
    def update(self, request, *args, **kwargs):
        try:
            product_id = kwargs.get('id')
            
            # Check if product exists
            try:
                instance = self.get_object()
            except Products.DoesNotExist:
                return Response(
                    {"error": f"Product with id {product_id} not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            except PermissionDenied as e:
                return Response(
                    {"error": str(e)}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Store old title for logging
            old_title = instance.title
            
            # Perform the update
            partial = kwargs.pop('partial', False)
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            # Get updated instance
            updated_instance = self.get_object()
            
            # Log user activity
            log_user_activity(
                request.user,
                'PRODUCT_UPDATE',
                f"Product '{old_title}' updated to '{updated_instance.title}'",
                request
            )
            
            # Clear cache
            self._clear_product_cache(product_id)
            
            logger.info(f"Product '{old_title}' updated by user {request.user.username} (ID: {request.user.id})")
            
            return Response({
                "message": "Product updated successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
            
        except PermissionDenied as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error updating product: {str(e)}")
            return Response(
                {"error": "Failed to update product", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def perform_update(self, serializer):
        """Custom update logic"""
        user = self.request.user
        
        # Save the updated product
        product = serializer.save()
        
        return product
    
    def _clear_product_cache(self, product_id):
        """Clear product-related cache after update"""
        try:
            redis_conn = get_redis_connection("default")
            cache_patterns = [
                f"product_{product_id}",
                f"product_detail_{product_id}", 
                f"product_with_images_{product_id}",
                f"product_images_{product_id}",
                "products_*"
            ]
            
            total_cleared = 0
            for pattern in cache_patterns:
                keys = redis_conn.keys(pattern)
                if keys:
                    redis_conn.delete(*keys)
                    total_cleared += len(keys)
            
            logger.info(f"Cleared {total_cleared} cache keys after product update")
        except Exception as e:
            logger.error(f"Error clearing cache after product update: {str(e)}")


# Product delet view
class ProductDeleteView(generics.DestroyAPIView):
    """Delete a specific product (soft delete by setting is_active=False)"""
    permission_classes = [IsAuthenticated, IsAdminOrVendor]
    serializer_class = ProductsSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        user = self.request.user
        # Admin can delete any product, vendors can only delete their own products
        if user.role == 'admin':
            return Products.objects.filter(is_active=True)
        elif user.role == 'vendor':
            return Products.objects.filter(vendor=user, is_active=True)
        else:
            return Products.objects.none()
    
    def get_object(self):
        """Override to add additional permission checks"""
        instance = super().get_object()
        user = self.request.user
        
        # Additional check: vendors can only delete their own products
        if user.role == 'vendor' and instance.vendor != user:
            raise PermissionDenied("You can only delete your own products.")
        
        return instance
    
    def destroy(self, request, *args, **kwargs):
        try:
            product_id = kwargs.get('id')
            
            # Check if product exists
            try:
                instance = self.get_object()
            except Products.DoesNotExist:
                return Response(
                    {"error": f"Product with id {product_id} not found or already deleted"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            except PermissionDenied as e:
                return Response(
                    {"error": str(e)}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Store product details for logging
            product_title = instance.title
            product_vendor = instance.vendor.username if instance.vendor else "Unknown"
            
            # Perform soft delete (set is_active=False instead of actual deletion)
            self.perform_destroy(instance)
            
            # Log user activity
            log_user_activity(
                request.user,
                'PRODUCT_DELETION',
                f"Product '{product_title}' (vendor: {product_vendor}) deleted",
                request
            )
            
            # Clear cache
            self._clear_product_cache(product_id)
            
            logger.info(f"Product '{product_title}' deleted by user {request.user.username} (ID: {request.user.id})")
            
            return Response({
                "message": "Product deleted successfully",
                "product_title": product_title,
                "deleted_at": instance.updated_at.isoformat() if hasattr(instance, 'updated_at') else None
            }, status=status.HTTP_200_OK)
            
        except PermissionDenied as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error deleting product: {str(e)}")
            return Response(
                {"error": "Failed to delete product", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def perform_destroy(self, instance):
        """Custom delete logic - soft delete instead of hard delete"""
        # Soft delete by setting is_active=False
        instance.is_active = False
        instance.save()
        
        # Also deactivate associated images (optional)
        ProductImage.objects.filter(product=instance).update(is_active=False)
        
        logger.info(f"Soft deleted product: {instance.title} (ID: {instance.id})")
    
    def _clear_product_cache(self, product_id):
        """Clear product-related cache after deletion"""
        try:
            redis_conn = get_redis_connection("default")
            cache_patterns = [
                f"product_{product_id}",
                f"product_detail_{product_id}",
                f"product_with_images_{product_id}",
                f"product_images_{product_id}",
                "products_*"
            ]
            
            total_cleared = 0
            for pattern in cache_patterns:
                keys = redis_conn.keys(pattern)
                if keys:
                    redis_conn.delete(*keys)
                    total_cleared += len(keys)
            
            logger.info(f"Cleared {total_cleared} cache keys after product deletion")
        except Exception as e:
            logger.error(f"Error clearing cache after product deletion: {str(e)}")


# Optional: Hard delete view for admin use only
class ProductHardDeleteView(generics.DestroyAPIView):
    """Permanently delete a product (admin only)"""
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = ProductsSerializer
    lookup_field = 'id'
    queryset = Products.objects.all()  # Include inactive products for hard delete
    
    def destroy(self, request, *args, **kwargs):
        try:
            product_id = kwargs.get('id')
            instance = self.get_object()
            
            # Store product details for logging
            product_title = instance.title
            product_vendor = instance.vendor.username if instance.vendor else "Unknown"
            
            # Delete associated images first
            ProductImage.objects.filter(product=instance).delete()
            
            # Perform hard delete
            instance.delete()
            
            # Log user activity
            log_user_activity(
                request.user,
                'PRODUCT_HARD_DELETION',
                f"Product '{product_title}' (vendor: {product_vendor}) permanently deleted",
                request
            )
            
            # Clear cache
            self._clear_product_cache(product_id)
            
            logger.warning(f"Product '{product_title}' permanently deleted by admin {request.user.username}")
            
            return Response({
                "message": "Product permanently deleted",
                "product_title": product_title
            }, status=status.HTTP_204_NO_CONTENT)
            
        except Products.DoesNotExist:
            return Response(
                {"error": f"Product with id {product_id} not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error hard deleting product: {str(e)}")
            return Response(
                {"error": "Failed to delete product", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _clear_product_cache(self, product_id):
        """Clear product-related cache after hard deletion"""
        try:
            redis_conn = get_redis_connection("default")
            cache_patterns = [
                f"product_{product_id}",
                f"product_detail_{product_id}",
                f"product_with_images_{product_id}",
                f"product_images_{product_id}",
                "products_*"
            ]
            
            total_cleared = 0
            for pattern in cache_patterns:
                keys = redis_conn.keys(pattern)
                if keys:
                    redis_conn.delete(*keys)
                    total_cleared += len(keys)
            
            logger.info(f"Cleared {total_cleared} cache keys after product hard deletion")
        except Exception as e:
            logger.error(f"Error clearing cache after product hard deletion: {str(e)}")

        




# View all the products
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


class ProductMetaDataListCreateView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    queryset = ProductMetaData.objects.filter(is_active=1).order_by('sort_order', 'name')
    serializer_class = ProductMetaDataSerializer
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ProductMetaDataListSerializer
        return ProductMetaDataSerializer
    
    def list(self, request, *args, **kwargs):
        # Check cache first
        cache_key = f"productmetadata_list_{request.GET.urlencode()}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.info(f"Cache hit for key: {cache_key}")
            return Response({"source": "cache", "data": cached_data})
        
        # If not in cache, get from database
        queryset = self.filter_queryset(self.get_queryset())
        
        # Filter by type if provided
        type_filter = request.GET.get('type')
        if type_filter and type_filter in ['category', 'unit']:
            queryset = queryset.filter(type=type_filter)
        
        serializer = self.get_serializer(queryset, many=True)
        
        # Cache the results for 15 minutes
        cache.set(cache_key, serializer.data, 60 * 15)
        logger.info(f"Data cached with key: {cache_key}")
        
        return Response({"source": "db", "data": serializer.data})
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Clear related cache
        self._clear_metadata_cache()
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def _clear_metadata_cache(self):
        """Clear all ProductMetaData related cache"""
        try:
            redis_conn = get_redis_connection("default")
            cache_pattern = "productmetadata_*"
            keys = redis_conn.keys(cache_pattern)
            if keys:
                redis_conn.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache keys matching {cache_pattern}")
        except Exception as e:
            logger.info(f"Error clearing cache: {str(e)}")


class ProductMetaDataDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [AllowAny]
    queryset = ProductMetaData.objects.all()
    serializer_class = ProductMetaDataSerializer
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        cache_key = f"productmetadata_detail_{instance.pk}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.info(f"Cache hit for detail key: {cache_key}")
            return Response({"source": "cache", "data": cached_data})
        
        serializer = self.get_serializer(instance)
        
        # Cache for 30 minutes
        cache.set(cache_key, serializer.data, 60 * 30)
        logger.info(f"Detail data cached with key: {cache_key}")
        
        return Response({"source": "db", "data": serializer.data})
    
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        
        # Clear related cache
        instance = self.get_object()
        self._clear_metadata_cache(instance.pk)
        
        return response
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance_pk = instance.pk
        
        response = super().destroy(request, *args, **kwargs)
        
        # Clear related cache
        self._clear_metadata_cache(instance_pk)
        
        return response
    
    def _clear_metadata_cache(self, instance_pk=None):
        """Clear ProductMetaData related cache"""
        redis_conn = get_redis_connection("default")
        
        # Clear list cache
        list_keys = redis_conn.keys("productmetadata_list_*")
        
        # Clear detail cache if instance_pk provided
        detail_keys = []
        if instance_pk:
            detail_keys = redis_conn.keys(f"productmetadata_detail_{instance_pk}")
        
        all_keys = list_keys + detail_keys
        if all_keys:
            redis_conn.delete(*all_keys)
            logger.info(f"Cleared {len(all_keys)} cache keys")


# @api_view(['GET'])
class ProductMetaDataByTypeView(APIView):
    """
    Get ProductMetaData filtered by type (category or unit)
    """
    permission_classes = [AllowAny]

    def get(self, request, metadata_type):
        if metadata_type not in ['category', 'unit']:
            return Response(
                {"error": "Invalid type. Must be 'category' or 'unit'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        cache_key = f"productmetadata_type_{metadata_type}"
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.info(f"Cache hit for type key: {cache_key}")
            return Response({"source": "cache", "data": cached_data})

        queryset = ProductMetaData.objects.filter(
            type=metadata_type,
            is_active=1
        ).order_by('sort_order', 'name')

        serializer = ProductMetaDataListSerializer(queryset, many=True)

        # Cache for 20 minutes
        cache.set(cache_key, serializer.data, 60 * 20)
        logger.info(f"Type data cached with key: {cache_key}")

        return Response({"source": "db", "data": serializer.data})


class ClearMetadataCacheView(APIView):
    """
    Manually clear all ProductMetaData cache (for admin use)
    """
    permission_classes = [IsAdmin]

    def post(self, request):
        try:
            redis_conn = get_redis_connection("default")
            cache_pattern = "productmetadata_*"
            keys = redis_conn.keys(cache_pattern)
            
            if keys:
                redis_conn.delete(*keys)
                return Response({
                    "message": f"Successfully cleared {len(keys)} cache keys",
                    "keys_cleared": len(keys)
                })
            else:
                return Response({"message": "No cache keys found to clear"})
                
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return Response(
                {"error": "Failed to clear cache"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


"""
    Product images views
"""
class ProductImageListCreateView(generics.ListCreateAPIView):
    """List all images for a product or add a new image"""
    permission_classes = [AllowAny]
    serializer_class = ProductImageUploadSerializer
    
    def get_queryset(self):
        product_id = self.kwargs.get('product_id')
        # Filter by product and ensure the product exists and is active
        return ProductImage.objects.filter(
            product_id=product_id, 
            product__is_active=True
        ).select_related('product')
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ProductImageSerializer
        return ProductImageUploadSerializer
    
    def list(self, request, *args, **kwargs):
        product_id = kwargs.get('product_id')
        cache_key = f"product_images_{product_id}"
        
        # Try Redis cache first
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response({"source": "cache", "data": cached_data})
        
        try:
            # Get queryset (this will be empty if product doesn't exist or is inactive)
            queryset = self.get_queryset()
            
            # Check if product exists by checking if we have any results or trying to get the product
            if not queryset.exists():
                # Check if it's because product doesn't exist or is inactive
                if not Products.objects.filter(id=product_id).exists():
                    return Response(
                        {"error": f"Product with id {product_id} not found"}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
                elif not Products.objects.filter(id=product_id, is_active=True).exists():
                    return Response(
                        {"error": "Product is not active"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Get product info for response
            product = Products.objects.get(id=product_id, is_active=True)
            
            # Serialize the images
            serializer = ProductImageSerializer(queryset, many=True)
            
            response_data = {
                "product_id": product_id,
                "product_title": product.title,
                "images": serializer.data
            }
            
            # Cache for 30 minutes
            cache.set(cache_key, response_data, timeout=60 * 30)
            logger.info(f"Product images cached: {cache_key}")
            
            return Response({"source": "db", "data": response_data})
            
        except Products.DoesNotExist:
            return Response(
                {"error": f"Product with id {product_id} not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error fetching product images: {str(e)}")
            return Response(
                {"error": "Service unavailable. Please try again later.", "details": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
    
    def create(self, request, *args, **kwargs):
        product_id = kwargs.get('product_id')
        
        # Check if product exists and is active
        try:
            product = Products.objects.get(id=product_id, is_active=True)
        except Products.DoesNotExist:
            return Response(
                {"error": f"Product with id {product_id} not found or inactive"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Add product to the request data
        data = request.data.copy()
        data['product'] = product_id
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Clear cache
        self._clear_product_cache(product_id)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def _clear_product_cache(self, product_id):
        """Clear product-related cache"""
        try:
            redis_conn = get_redis_connection("default")
            cache_patterns = [
                f"product_images_{product_id}",
                f"product_detail_{product_id}",
                "products_*"
            ]
            
            total_cleared = 0
            for pattern in cache_patterns:
                keys = redis_conn.keys(pattern)
                if keys:
                    redis_conn.delete(*keys)
                    total_cleared += len(keys)
            
            logger.info(f"Cleared {total_cleared} cache keys for product {product_id}")
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            

class ProductImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a specific product image"""
    permission_classes = [AllowAny]
    serializer_class = ProductImageSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        product_id = self.kwargs.get('product_id')
        # Use the queryset filtering to handle product validation
        return ProductImage.objects.filter(
            product_id=product_id,
            product__is_active=True
        ).select_related('product')
    
    def retrieve(self, request, *args, **kwargs):
        product_id = kwargs.get('product_id')
        image_id = kwargs.get('id')
        cache_key = f"product_image_{product_id}_{image_id}"
        
        # Try Redis cache first
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response({"source": "cache", "data": cached_data})
        
        try:
            # Get the image using the filtered queryset
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            data = serializer.data
            
            # Cache for 30 minutes
            cache.set(cache_key, data, timeout=60 * 30)
            
            return Response({"source": "db", "data": data})
            
        except ProductImage.DoesNotExist:
            return Response(
                {"error": f"Image with id {image_id} not found for product {product_id}"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error fetching product image: {str(e)}")
            return Response(
                {"error": "Service unavailable. Please try again later.", "details": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
    
    def update(self, request, *args, **kwargs):
        try:
            response = super().update(request, *args, **kwargs)
            
            # Clear cache after update
            product_id = self.kwargs.get('product_id')
            image_id = self.kwargs.get('id')
            cache.delete(f"product_image_{product_id}_{image_id}")
            cache.delete(f"product_images_{product_id}")
            cache.delete("products_list")
            
            return response
            
        except Exception as e:
            logger.error(f"Error updating product image: {str(e)}")
            return Response(
                {"error": "Failed to update image", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        try:
            product_id = self.kwargs.get('product_id')
            image_id = self.kwargs.get('id')
            
            response = super().destroy(request, *args, **kwargs)
            
            # Clear cache after deletion
            cache.delete(f"product_image_{product_id}_{image_id}")
            cache.delete(f"product_images_{product_id}")
            cache.delete("products_list")
            
            return response
            
        except Exception as e:
            logger.error(f"Error deleting product image: {str(e)}")
            return Response(
                {"error": "Failed to delete image", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BulkImageUploadView(APIView):
    """Upload multiple images to a product at once"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            serializer = BulkImageUploadSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            product_id = serializer.validated_data['product_id']
            image_urls = serializer.validated_data['image_urls']
            
            # Verify product exists and is active
            try:
                product = Products.objects.get(id=product_id, is_active=True)
            except Products.DoesNotExist:
                return Response(
                    {"error": f"Product with id {product_id} not found or inactive"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Create image records
            images_to_create = []
            for url in image_urls:
                images_to_create.append(ProductImage(product=product, image_url=url.strip()))
            
            # Bulk create images
            created_images = ProductImage.objects.bulk_create(images_to_create)
            
            # Clear related cache
            cache.delete(f"product_images_{product_id}")
            cache.delete(f"product_detail_{product_id}")
            cache.delete("products_list")
            
            # Serialize the created images for response
            response_data = []
            for img in created_images:
                response_data.append({
                    'id': img.id,
                    'image_url': img.image_url
                })
            
            return Response({
                "message": f"Successfully uploaded {len(created_images)} images",
                "product_id": product_id,
                "product_title": product.title,
                "images": response_data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error in bulk image upload: {str(e)}")
            return Response(
                {"error": "Failed to upload images", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ProductWithImagesView(generics.RetrieveAPIView):
    """Get a product with all its images"""
    permission_classes = [AllowAny]
    serializer_class = ProductWithImagesSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        return Products.objects.filter(is_active=True).prefetch_related('images').select_related('category')
    
    def retrieve(self, request, *args, **kwargs):
        product_id = kwargs.get('id')
        cache_key = f"product_with_images_{product_id}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.info(f"Cache hit for product with images: {cache_key}")
            return Response({"source": "cache", "data": cached_data})
        
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Cache for 30 minutes
        cache.set(cache_key, serializer.data, 60 * 30)
        logger.info(f"Product with images cached: {cache_key}")
        
        return Response({"source": "db", "data": serializer.data})