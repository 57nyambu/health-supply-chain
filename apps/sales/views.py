from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from .models import Order, OrderItem, Customer
from apps.products.models import Product
from apps.integrations.mpesa import MpesaGateway

class POSView(View):
    """Handle barcode scanning + checkout."""
    def get(self, request):
        products = Product.objects.filter(is_active=True)
        return render(request, 'sales/pos.html', {'products': products})

    def post(self, request):
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))
        customer_phone = request.POST.get('customer_phone')

        # Create or fetch customer
        customer, _ = Customer.objects.get_or_create(
            phone=customer_phone,
            defaults={'name': f"Customer {customer_phone}"}
        )

        # Create order
        order = Order.objects.create(
            customer=customer,
            warehouse=request.user.warehouse  # Assumes user has warehouse linked
        )

        # Add item
        product = Product.objects.get(id=product_id)
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            unit_price=product.selling_price
        )

        order.calculate_totals()
        return JsonResponse({
            'order_id': order.id,
            'total': order.total
        })

class ProcessPaymentView(View):
    """Handle M-Pesa payment."""
    def post(self, request):
        order_id = request.POST.get('order_id')
        phone = request.POST.get('phone')  # Format: 254712345678

        order = Order.objects.get(id=order_id)
        mpesa = MpesaGateway()
        response = mpesa.stk_push(
            phone=phone,
            amount=order.total,
            order_id=order_id,
            description=f"Payment for Order #{order.order_number}"
        )

        return JsonResponse(response)