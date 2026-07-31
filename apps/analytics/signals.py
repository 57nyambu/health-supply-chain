from django.db.models.signals import post_save
from django.dispatch import receiver
from sales.models import Order
from products.models import Inventory
from .models import RTInventoryAlert, SalesReport

@receiver(post_save, sender=Order)
def update_sales_metrics(sender, instance, **kwargs):
    """Update real-time sales dashboards on new orders."""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'sales_updates',
        {
            'type': 'order.update',
            'order_id': instance.id,
            'total': float(instance.total)
        }
    )

@receiver(post_save, sender=Inventory)
def check_low_stock(sender, instance, **kwargs):
    """Generate alerts when stock <= reorder_level."""
    if instance.quantity <= instance.product.reorder_level:
        RTInventoryAlert.objects.get_or_create(
            product=instance.product,
            warehouse=instance.warehouse,
            defaults={'current_stock': instance.quantity}
        )