from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Receipt, Order
from apps.integrations.sms import SMSService

@receiver(post_save, sender=Receipt)
def send_sms_receipt(sender, instance, created, **kwargs):
    if created and not instance.sms_sent and instance.order.customer and instance.order.customer.phone:
        sms = SMSService()
        message = (
            f"Receipt #{instance.receipt_number}\n"
            f"Amount: KES {instance.order.total}\n"
            f"Items: {instance.order.items.count()}\n"
            f"Thank you!"
        )
        try:
            sms.send_receipt(instance.order.customer.phone, message)
            instance.sms_sent = True
            instance.sms_status = "Sent"
        except Exception as e:
            instance.sms_status = f"Failed: {e}"
        instance.save(update_fields=['sms_sent', 'sms_status'])

@receiver(pre_save, sender=Order)
def notify_order_status_change(sender, instance, **kwargs):
    if not instance.pk:
        return  # Only notify on updates, not creation

    try:
        previous = Order.objects.get(pk=instance.pk)
    except Order.DoesNotExist:
        return

    sms = SMSService()
    customer = instance.customer
    if not customer or not customer.phone:
        return

    # Notify on status change
    if previous.status != instance.status:
        if instance.status == 'PAID':
            message = (
                f"Order #{instance.order_number} payment received.\n"
                f"Amount: KES {instance.total}\n"
                f"Thank you for your purchase!"
            )
            sms.send_sms(customer.phone, message, model="OrderStatus")
        elif instance.status == 'DELIVERED':
            message = (
                f"Order #{instance.order_number} has been delivered.\n"
                f"Thank you for shopping with us!"
            )
            sms.send_sms(customer.phone, message, model="OrderStatus")
        elif instance.status == 'CANCELLED':
            message = (
                f"Order #{instance.order_number} has been cancelled.\n"
                f"If you have questions, contact support."
            )
            sms.send_sms(customer.phone, message, model="OrderStatus")