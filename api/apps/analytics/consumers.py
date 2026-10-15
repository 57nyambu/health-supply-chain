import json
from channels.generic.websocket import AsyncWebsocketConsumer

class SalesDashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add(
            "sales_updates",
            self.channel_name
        )
        await self.accept()

    async def order_update(self, event):
        """Send real-time order data to frontend."""
        await self.send(text_data=json.dumps({
            'order_id': event['order_id'],
            'total': event['total'],
            'type': 'new_order'
        }))