from django.contrib import admin
from .models import Category, Banner, Product, CartItem, Order, OrderItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('id', 'name')


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('title',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'category', 'price', 'stock',
        'is_active', 'is_featured'
    )
    list_filter = ('category', 'is_active', 'is_featured')
    list_editable = ('price', 'stock', 'is_active', 'is_featured')
    search_fields = ('name',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        'product', 'product_name', 'price', 'quantity'
    )
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'total_amount', 'status', 'created_at'
    )
    list_filter = ('status', 'created_at')
    list_editable = ('status',)
    search_fields = ('full_name', 'phone', 'user__username')
    inlines = [OrderItemInline]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'quantity')