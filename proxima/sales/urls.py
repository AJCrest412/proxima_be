# sales/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClientViewSet, SaleViewSet, SaleItemChoicesView, SaleItemListView

router = DefaultRouter()
router.register('clients', ClientViewSet, basename='client')
router.register('sales', SaleViewSet, basename='sale')

urlpatterns = [
    path('', include(router.urls)),
    path('choices/', SaleItemChoicesView.as_view(), name='sale-item-choices'),
    path('sale-items/', SaleItemListView.as_view(), name='sale-items-list'),
]