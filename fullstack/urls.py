from django.urls import path, include
from . import  views


from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter

router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet)
router.register(r'products', views.ProductViewSet)
router.register(r'cart', views.CartViewSet, basename='cart')
router.register(r'cart/items', views.CartItemViewSet, basename='cart-items')
router.register(r'create-checkout-session', views.CreateCheckoutSessionViewSet, basename='create-checkout-session')
router.register(r'orders', views.OrderViewSet, basename='order')

orders_router = NestedDefaultRouter(router, r'orders', lookup='order')
orders_router.register(r'items', views.OrderItemViewSet, basename='order-items')

# URL Configuration
urlpatterns = [
    path('', include(router.urls)), 
    path('webhook/stripe/', views.stripe_webhook, name='stripe-webhook'),
    path('', include(orders_router.urls)),
]
