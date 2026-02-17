from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from .models import Category, Product, Cart, CartItem, Review, Order,OrderItem
from .serializers import CategorySerializer, ProductSerializer, CartSerializer, CartItemSerializer,  ReviewSerializer, UserSerializer, CustomTokenSerializer,OrderSerializer, OrderItemSerializer
from django.contrib.auth.models import User
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
import stripe
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from .serializers import CartSerializer
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.http import JsonResponse
from django.http import FileResponse
from .utils import generate_invoice
from .serializers import CustomTokenSerializer
from django.middleware.csrf import get_token
from .cookies import csrf_cookie_kwargs
  


class CsrfView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = get_token(request)  # forces token creation
        res = Response({"csrfToken": token})
        res.set_cookie("csrftoken", token, **csrf_cookie_kwargs())
        return res

class RegisterUser(generics.ListCreateAPIView ):
    queryset = User.objects.all()
    serializer_class= UserSerializer
    permission_classes= [AllowAny]

class Testauthentication(generics.GenericAPIView):
    permission_classes=[IsAuthenticated]
    
    def get(self, request):
        data = {
         'mg':'its works'
        }
        return Response(data, status=status.HTTP_200_OK)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = StandardResultsSetPagination
    lookup_field = 'slug'

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = StandardResultsSetPagination
    lookup_field = 'slug'

    
class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return Cart.objects.filter(user=user)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().first()  
        serializer = self.get_serializer(queryset)
        return Response(serializer.data)
    
    
    
class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:  # Admins can see all orders
            return Order.objects.all().order_by("-created_at")
        return Order.objects.filter(user=user).order_by("-created_at")

    @action(detail=True, methods=["get"])
    def invoice(self, request, pk=None):
        """Download invoice PDF"""
        order = self.get_object()
        buffer = generate_invoice(order)
        return FileResponse(buffer, as_attachment=True, filename=f"invoice_{order.id}.pdf")

class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return OrderItem.objects.all()
        return OrderItem.objects.filter(order__user=user)
    
    
class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_cart(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart

    def get_queryset(self):
        cart = self.get_cart()
        return CartItem.objects.filter(cart=cart)
    
    
    
    @action(detail=False, methods=['post'])
    def add_item(self, request):
           cart = self.get_cart()
           product = get_object_or_404(Product, pk=request.data['product_id'])
           quantity = int(request.data['quantity'])
           cart_item, created = CartItem.objects.get_or_create(cart=cart,product=product,defaults={"quantity": quantity})
           if not created:
                cart_item.quantity += quantity
                cart_item.save()
           serializer = self.get_serializer(cart_item)
           return Response({'message': 'Item added to cart', 'cart_item': serializer.data}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    

    @action(detail=True, methods=['patch'])
    def update_quantity(self, request, pk=None):
        item = self.get_object()
        action = request.data.get('action', 'increment')

        if action == 'increment':
            item.quantity += 1
        elif action == 'decrement' and item.quantity > 1:
            item.quantity -= 1

        item.save()
        return Response({'quantity': item.quantity})
   
   
    @action(detail=True, methods=['delete'])
    def remove_item(self, request, pk=None):
        cart_item = self.get_object()
        cart_item.delete()
        return Response({'message': 'Item removed from cart'}, status=status.HTTP_200_OK)

class ReviewViewSet(viewsets.ModelViewSet):
    
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    


stripe.api_key = settings.STRIPE_SECRET_KEY

class CreateCheckoutSessionViewSet(viewsets.ModelViewSet):
    '''permission_classes = [IsAuthenticated]'''

    @action(detail=False, methods=['post'])
    def payment(self, request):
        cart = Cart.objects.get(user=request.user)
        cart_items = CartItem.objects.filter(cart__user=request.user)
        cart_total_price=sum(item.product.price * item.quantity for item in cart_items)


        if not cart_items.exists():
            return Response({"error": "Cart is empty"}, status=400)

        

        order = Order.objects.create(
            user=request.user,
            total_price=cart_total_price,
            status="pending"
            )

        # Add Order Items
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,
            )


        line_items = []
        for item in cart_items:
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": item.product.name,
                    },
                    "unit_amount": int(item.product.price * 100),  # Stripe expects cents
                },
                "quantity": item.quantity,
            })

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items= line_items,
            mode="payment",
            success_url=f"{settings.DOMAIN}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.DOMAIN}/cancel",
            metadata={'order_id': str(order.id)},
           payment_intent_data={'metadata': {'order_id': str(order.id)}}
        )


        order.stripe_session_id = session.id
        order.save()

        return Response({"checkout_url": session.url})

@csrf_exempt
def stripe_webhook(request):
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    if not sig_header:
        return JsonResponse({'error': 'Missing signature'}, status=400)
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        
        
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        return JsonResponse({'error': str(e)}, status=400)
    
    
    if event['type'] == 'checkout.session.completed':
       session = event['data']['object']
       order_id = session.get('metadata', {}).get('order_id')

    
       if not order_id and session.get("payment_intent"):
           payment_intent = stripe.PaymentIntent.retrieve(session["payment_intent"])
           order_id = payment_intent.metadata.get("order_id")

       if not order_id:
        return JsonResponse({'error': 'No order ID'}, status=400)

       try:
          order = Order.objects.get(id=order_id)
          order.status = 'paid'
          order.save()
          
          try:
            cart = Cart.objects.get(user=order.user)
            cart.items.all().delete()
          except Cart.DoesNotExist:
               pass
          
          return JsonResponse({'status': 'success'})
       except Order.DoesNotExist:
          return JsonResponse({'error': 'Order not found'}, status=404)
    return JsonResponse({'status': 'handled'})
    