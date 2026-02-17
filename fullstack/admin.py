from django.contrib import admin

from .models import Category, Product, ProductImage, Cart, CartItem, Review, Order,OrderItem, AuthSession, SessionRefreshToken

# Register your models here.
#admin.site.register(Artiste)
#admin.site.register(Album)
#admin.site.register(Track)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]
    prepopulated_fields = {'slug': ('name',)}

admin.site.register(Product, ProductAdmin)
admin.site.register(Category)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Review)
admin.site.register(AuthSession)
admin.site.register(SessionRefreshToken)


