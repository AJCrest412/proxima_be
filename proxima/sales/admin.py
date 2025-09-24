from django.contrib import admin
from .models import Client, Sale, SaleItem

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'arc_name', 'created_at')
    search_fields = ('name', 'phone', 'arc_name')

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_by', 'client', 'status', 'created_at', 'total_amount_display')
    list_filter = ('status', 'created_at')
    search_fields = ('client__name', 'created_by__username')

    def total_amount_display(self, obj):
        return obj.total_amount
    total_amount_display.short_description = 'Total Amount'

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'category', 'quantity', 'mrp', 'discount_type', 'discount_value', 'price_per_piece', 'total_amount')
    list_filter = ('category', 'discount_type')
    search_fields = ('product_name', 'room')