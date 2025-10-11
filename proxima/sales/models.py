from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class Client(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    attend_by = models.CharField(max_length=255, blank=True, null=True)
    arc_name = models.CharField(max_length=255, blank=True, null=True)
    arc_phone = models.CharField(max_length=20, blank=True, null=True)
    arc_address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or f"Client {self.id}"

class Sale(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
    ]
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_amount(self):
        total = Decimal('0.00')
        for item in self.items.all():
            total += (item.total_amount or Decimal('0.00'))
        return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def __str__(self):
        return f"Sale #{self.id} ({self.status})"

class SaleItem(models.Model):
    CATEGORY_CHOICES = [
        ("Hardware", "Hardware"),
        ("Lamination & Highlighter", "Lamination & Highlighter"),
        ("Veneer", "Veneer"),
        ("Sofa_durtains", "Sofa & Curtains"),
        ("Modular", "Modular"),
    ]
    DISCOUNT_TYPE_CHOICES = [
        ("percent", "Percent"),
        ("amount", "Amount"),
    ]
    sale = models.ForeignKey(Sale, related_name="items", on_delete=models.CASCADE)
    room = models.CharField(max_length=100, blank=True, null=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    product_name = models.CharField(max_length=255)
    product_code = models.CharField(max_length=100, blank=True, null=True)
    size_finish = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    mrp = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default="amount")
    discount_value = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0.00'))])
    price_per_piece = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0.00'))])
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0.00'))])


    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validate discount value based on type
        if self.discount_type == "percent" and self.discount_value > 100:
            raise ValidationError({'discount_value': 'Percentage discount cannot exceed 100%.'})
        
        # Validate that discount doesn't exceed MRP for amount type
        if self.discount_type == "amount" and self.discount_value > self.mrp:
            raise ValidationError({'discount_value': 'Discount amount cannot exceed MRP.'})

    def calculate_prices(self):
        # ensure Decimal usage
        qty = Decimal(self.quantity)
        mrp = Decimal(self.mrp)
        disc = Decimal(self.discount_value or 0)

        if self.discount_type == "percent":
            per_piece = mrp - (mrp * disc / Decimal('100'))
        else:
            per_piece = mrp - disc

        # do not allow negative price
        if per_piece < Decimal('0.00'):
            per_piece = Decimal('0.00')

        total = (per_piece * qty)
        # round to 2 decimals
        per_piece = per_piece.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total = total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return per_piece, total

    def save(self, *args, **kwargs):
        self.full_clean()  # This calls clean() method for validation
        per_piece, total = self.calculate_prices()
        self.price_per_piece = per_piece
        self.total_amount = total
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product_name} x{self.quantity} (Sale {self.sale_id})"