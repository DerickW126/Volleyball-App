import json
from channels.generic.websocket import AsyncWebsocketConsumer
import logging

# Set up logging
logger = logging.getLogger(__name__)

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Extract user_id from the URL route
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.group_name = f'notifications_{self.user_id}'
        
        print(f"User ID: {self.user_id} is attempting to connect to WebSocket.")
        
        # Add this channel to the group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.debug(f"WebSocket connection accepted for User ID: {self.user_id}")

    async def disconnect(self, close_code):
        # Remove this channel from the group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        logger.debug(f"WebSocket connection closed for User ID: {self.user_id}")
    '''
    async def receive(self, text_data):
        # Handle incoming data if needed
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message')
        
        logger.debug(f"Received message from User ID: {self.user_id}: {message}")
        
        # You can handle incoming messages here if needed
        # For example, broadcast the message to the group
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'send_notification',
                'message': message
            }
        )
    '''
    async def send_notification(self, event):
    # Safely get the message, default to a warning if missing
        notification = event.get('notification', {})
        message = notification.get('message', "No message provided")
        
        if message == "No message provided":
            # Log a warning or handle the situation as needed
            logger.warning(f"Notification received without a 'message': {event}")
        
        # Send the notification data to the WebSocket client
        await self.send(text_data=json.dumps({'message': message}))
        logger.debug(f"Sent notification to User ID: {self.user_id}: {message}")

