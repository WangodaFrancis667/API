from django.urls import path
from .views import CategoriesListView, ProductView, ProductFullView, ProductDetailView, ProductMetaDataView

urlpatterns = [
    path('categories/', CategoriesListView.as_view(), name='view-categories'),
    path('products/', ProductFullView.as_view(), name='view-products'),

    path('product-details/', ProductDetailView.as_view(), name='product-details'),
    path('product-list/', ProductView.as_view(), name='product-list'),

    path('product-metadata/', ProductMetaDataView.as_view(), name='product-metadata'),
]