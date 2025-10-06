from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Client, Sale, SaleItem
from .serializers import ClientSerializer, SaleSerializer, SaleItemSerializer, SaleWithClientUpdateSerializer
from rest_framework.views import APIView
from django.db.models import Q
from .pagination import CustomPagination


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all().order_by('-created_at')
    serializer_class = ClientSerializer
    pagination_class = CustomPagination 

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(phone__icontains=search) |
                Q(arc_name__icontains=search)
            )
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            return Response({
                "success": True,
                "message": "Clients retrieved successfully.",
                "data": response.data
            })

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "success": True,
            "message": "Clients retrieved successfully.",
            "data": serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        client = self.get_object()
        client_name = str(client)

        client.delete()

        return Response({
            "success": True,
            "message": f"Client '{client_name}' and all related sales/items deleted successfully."
        }, status=status.HTTP_200_OK)

class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all().order_by('-created_at')
    serializer_class = SaleSerializer

    def get_queryset(self):

        queryset = Sale.objects.all().order_by('-created_at')
        client_id = self.request.query_params.get('client_id')
        room = self.request.query_params.get('room')
        print(room)

        if client_id:
            queryset = queryset.filter(client__id=client_id)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "success": True,
            "message": "Sales retrieved successfully.",
            "data": serializer.data
        })

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            "success": True,
            "message": "Sale retrieved successfully.",
            "data": serializer.data
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({
            "success": True,
            "message": "Sale created successfully.",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)


    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        sale = self.get_object()
        if sale.status != 'draft':
            return Response({"success" : False, "message": "Only draft sales can be confirmed."}, status=status.HTTP_400_BAD_REQUEST)

        client_id = request.data.get('client_id')
        client_data = request.data.get('client')

        if client_id:
            try:
                client = Client.objects.get(id=client_id)
            except Client.DoesNotExist:
                return Response({"success" : False, "message": "Client not found."}, status=status.HTTP_404_NOT_FOUND)
        elif client_data:
            client_serializer = ClientSerializer(data=client_data)
            client_serializer.is_valid(raise_exception=True)
            client = client_serializer.save()
        else:
            return Response({"success" : False, "message": "Provide client_id or client data."}, status=status.HTTP_400_BAD_REQUEST)

        sale.client = client
        sale.status = 'confirmed'
        sale.save()
        return Response({"success" : True, "message": "Sale confirmed successfully.", "data": self.get_serializer(sale).data})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        sale = self.get_object()
        if sale.status == 'cancelled':
            return Response({"success" : False, "message": "Sale already cancelled."}, status=status.HTTP_400_BAD_REQUEST)
        sale.status = 'cancelled'
        sale.save()
        return Response({"success" : True, "message": "Sale cancelled successfully.", "data": self.get_serializer(sale).data})

    @action(detail=True, methods=['post'])
    def add_items(self, request, pk=None):
        sale = self.get_object()
        if sale.status == 'cancelled':
            return Response({"success" : False, "message": "Cannot modify a cancelled sale."}, status=status.HTTP_400_BAD_REQUEST)

        items_data = request.data.get('items')
        if not items_data or not isinstance(items_data, list):
            return Response({"success" : False, "message": "Provide a list of items."}, status=status.HTTP_400_BAD_REQUEST)

        for item_data in items_data:
            serializer = SaleItemSerializer(data=item_data)
            serializer.is_valid(raise_exception=True)
            serializer.save(sale=sale)

        return Response({"success" : True, "message": "Items added successfully.", "data": self.get_serializer(sale).data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def remove_items(self, request, pk=None):
        sale = self.get_object()
        if sale.status == 'cancelled':
            return Response({"success" : False, "message": "Cannot modify a cancelled sale."}, status=status.HTTP_400_BAD_REQUEST)

        items_ids = request.data.get('items')
        if not items_ids or not isinstance(items_ids, list):
            return Response({"success" : False, "message": "Provide a list of item IDs."}, status=status.HTTP_400_BAD_REQUEST)

        items = sale.items.filter(id__in=items_ids)
        count = items.count()
        items.delete()

        return Response({"success" : True, "message": f"{count} item(s) removed from the sale."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['put', 'patch'])
    def update_with_client(self, request, pk=None):
        """
        Simple API to update sale with client and items data.
        
        Pass:
        - client_id: to assign existing client
        - client_data: {client data} to update/create client
        - items: [{item data}] to update items
        - status: to update sale status
        
        Example:
        {
            "client_id": 5,
            "client_data": {"name": "Updated Name", "phone": "1234567890"},
            "items": [{"product_name": "Product 1", "quantity": 2, "mrp": "100.00"}],
            "status": "confirmed"
        }
        """
        sale = self.get_object()
        
        # Check if sale can be modified
        if sale.status == 'cancelled':
            return Response({
                "success": False, 
                "message": "Cannot modify a cancelled sale."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Use the serializer for updating
        serializer = SaleWithClientUpdateSerializer(sale, data=request.data, partial=request.method == 'PATCH')
        serializer.is_valid(raise_exception=True)
        updated_sale = serializer.save()

        return Response({
            "success": True,
            "message": "Sale updated successfully.",
            "data": SaleSerializer(updated_sale).data
        }, status=status.HTTP_200_OK)

class SaleItemChoicesView(APIView):

    def get(self, request):
        categories = [name for code, name in SaleItem.CATEGORY_CHOICES]
        discount_types = [name for code, name in SaleItem.DISCOUNT_TYPE_CHOICES]
        
        return Response({
            "categories": categories,
            "discount_types": discount_types,
        })
    
class SaleItemListView(APIView):

    def get(self, request, *args, **kwargs):
        sale_id = request.query_params.get('sale_id')
        room = request.query_params.get('room')

        if not sale_id:
            return Response({"success": False, "message": "sale_id is required.", "data": []},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            sale = Sale.objects.get(id=sale_id)
        except Sale.DoesNotExist:
            return Response({"success": False, "message": "Sale not found.", "data": []},
                            status=status.HTTP_404_NOT_FOUND)

        items = sale.items.all()
        
        if room:
            items = items.filter(room__icontains=room)

        serializer = SaleItemSerializer(items, many=True)
        return Response({
            "success": True,
            "message": "Sale items retrieved successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)