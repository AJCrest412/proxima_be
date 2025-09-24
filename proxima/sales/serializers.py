from rest_framework import serializers
from decimal import Decimal
from .models import Client, Sale, SaleItem

class SaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        read_only_fields = ('price_per_piece', 'total_amount', 'sale')
        fields = '__all__'

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0.")
        return value

    def validate_mrp(self, value):
        if value <= 0:
            raise serializers.ValidationError("MRP must be greater than 0.")
        return value

    def validate_discount_value(self, value):
        if value < 0:
            raise serializers.ValidationError("Discount value cannot be negative.")
        return value

    def validate(self, data):
        # Validate discount logic
        discount_type = data.get('discount_type')
        discount_value = data.get('discount_value', 0)
        mrp = data.get('mrp')

        if discount_type == 'percent' and discount_value > 100:
            raise serializers.ValidationError({
                'discount_value': 'Percentage discount cannot exceed 100%.'
            })
        
        if discount_type == 'amount' and mrp and discount_value > mrp:
            raise serializers.ValidationError({
                'discount_value': 'Discount amount cannot exceed MRP.'
            })

        return data

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Client name is required.")
        return value.strip()
    
class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, required=False)
    total_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True,)
    created_by = serializers.StringRelatedField(read_only=True)
    client = ClientSerializer(read_only=True) 
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(), source='client', write_only=True, required=False
    )

    class Meta:
        model = Sale
        fields = ['id', 'created_by', 'client', 'status', 'created_at', 'items', 'total_amount', 'client_id']
        read_only_fields = ['created_by', 'created_at', 'total_amount']

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user
        
        items_data = validated_data.pop('items', [])
        validated_data.pop('created_by', None)

        sale = Sale.objects.create(created_by=user, **validated_data)
        
        # Create sale items if provided
        for item_data in items_data:
            SaleItem.objects.create(sale=sale, **item_data)
        
        return sale

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        
        # Update sale fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update items if provided
        if items_data is not None:
            # Delete existing items
            instance.items.all().delete()
            # Create new items
            for item_data in items_data:
                SaleItem.objects.create(sale=instance, **item_data)
        
        return instance

