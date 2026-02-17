from rest_framework import serializers
from .models import Category, Product, Cart, CartItem,Review, ProductImage, Order,OrderItem
from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import re
   
class UserSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = User
        fields = ['id','username','password']   
        extra_kwargs={'password':{'write_only':True}}
        
    def create(self, validated_data):
        user= User.objects.create_user(**validated_data)
        return user
   
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username is already taken")
        return value
    
    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters long"
            )

        if not re.search(r"[A-Za-z]", value):
            raise serializers.ValidationError(
                "Password must contain at least one letter"
            )

        if not re.search(r"\d", value):
            raise serializers.ValidationError(
                "Password must contain at least one number"
            )

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise serializers.ValidationError(
                "Password must contain at least one symbol"
            )

        return value

    

class CustomTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls,user):
        token = super().get_token(user)
        token['username'] = user.username
        return token



class ReviewSerializer(serializers.ModelSerializer):
    

    class Meta:
        model = Review
        fields = ['id', 'rating', 'comment', 'created_at']

class ProductImageSerializer(serializers.ModelSerializer):
    product = serializers.CharField(source='product.name')
    class Meta:
        model = ProductImage
        fields = ['id', 'product','image', 'is_primary']


class ProductSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    category = serializers.CharField(source='category.slug')
    images = ProductImageSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    
    class Meta:
        model = Product
        fields = ('id', 'category', 'name', 'slug', 'images','description', 'price', 'stock', 'created_at', 'reviews')

class CategorySerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'products']

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    product_price = serializers.CharField(source="product.price", read_only=True)
    total_price = serializers.SerializerMethodField(method_name="total")

    class Meta:
        model = CartItem
        fields = ["id","product", "product_id", "quantity", "product_price", "total_price"]
        
    def total(self, obj):
        return obj.product.price * obj.quantity

    
    
class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    cart_total_price = serializers.SerializerMethodField(method_name='total_price')
    cart_total_quantity = serializers.SerializerMethodField(method_name='total_quantity')
    
    def total_price(self, obj):
        items = obj.items.all()
        return sum(item.product.price * item.quantity for item in items )
    
    def total_quantity(self, obj):
        return sum( item.quantity for item in obj.items.all())
    
    class Meta:
        model = Cart
        fields = ('id','user' ,'items', 'cart_total_price','cart_total_quantity','created_at')

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "quantity", "price", "subtotal"]

    def get_subtotal(self, obj):
        return obj.subtotal


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Order
        fields = ["id", "user", "total_price", "status", "created_at", "items"]