from django.urls import path
from .views import (
    CategoriesListView, ClearMetadataCacheView ,ProductMetaDataByTypeView ,
    ProductMetaDataDetailView ,ProductView, ProductFullView, 
    ProductDetailView, ProductMetaDataListCreateView, ProductImageListCreateView,
    ProductImageDetailView, BulkImageUploadView, ProductWithImagesView,
    ProductCreateView, ProductUpdateView, ProductDeleteView, ProductHardDeleteView,
)

urlpatterns = [
    path('categories/', CategoriesListView.as_view(), name='view-categories'),

    # Product CRUD management endpoints
    path('create/', ProductCreateView.as_view(), name='create-product'),
    path('<int:id>/update/', ProductUpdateView.as_view(), name='update-product'),
    path('<int:id>/delete/', ProductDeleteView.as_view(), name='delete-product'),
    path('<int:id>/hard-delete/', ProductHardDeleteView.as_view(), name='hard-delete-product'),

    # Product view endpoints
    path('view-products/', ProductFullView.as_view(), name='view-products'),
    path('product-details/<int:id>/', ProductDetailView.as_view(), name='product-details'),
    path('product-list/', ProductView.as_view(), name='product-list'),

    # Product Image endpoints
    path('<int:product_id>/images/', ProductImageListCreateView.as_view(), name='product-images-list-create'),
    path('<int:product_id>/images/<int:id>/', ProductImageDetailView.as_view(), name='product-image-detail'),
    path('images/bulk-upload/', BulkImageUploadView.as_view(), name='bulk-image-upload'),
    path('<int:id>/with-images/', ProductWithImagesView.as_view(), name='product-with-images'),

    # ProductMetaData endpoints
    path('metadata/', ProductMetaDataListCreateView.as_view(), name='metadata-list-create'),
    path('metadata/<int:pk>/', ProductMetaDataDetailView.as_view(), name='metadata-detail'),
    path('metadata/type/<str:metadata_type>/', ProductMetaDataByTypeView.as_view(), name='metadata-by-type'),
    path('metadata/clear-cache/', ClearMetadataCacheView.as_view(), name='clear-metadata-cache'),
]
