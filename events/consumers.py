import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
from asgiref.sync import sync_to_async
from .serializers import ChatMessageSerializer
from .views import notify_user_about_event

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.event_id = self.scope['url_route']['kwargs']['event_id']
        print(f'Successfully connected to event {self.event_id}')
        
        # Join the chat room group
        await self.channel_layer.group_add(
            self.event_id,
            self.channel_name
        )
        await self.accept()
        
        # Send old messages when a new user connects
        messages = await self.get_old_messages()
        for message in messages:
            await self.send(text_data=json.dumps(message))
        
    async def disconnect(self, close_code):
        # Leave the chat room group
        await self.channel_layer.group_discard(
            self.event_id,
            self.channel_name
        )
        print(f'Disconnected from event {self.event_id}')
    
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json.get('message')
            user_id = self.scope['user'].id
            
            print(f'Received message: {message} from user {user_id}')
            
            if not message:
                raise ValueError("Message content is empty or not provided")
            
            # Save the message to the database
            await self.save_message(user_id, message)
            await self.notify_users_about_event(user_id, message)
            
            # Broadcast message to the chat room group
            await self.channel_layer.group_send(
                self.event_id,
                {
                    'type': 'chat_message',
                    'message': message,
                    'user_id': user_id,
                    'user_nickname': self.scope['user'].nickname,
                    'user_first_name': self.scope['user'].first_name,
                    'user_last_name': self.scope['user'].last_name,
                    'timestamp': timezone.now().isoformat()
                }
            )
            
            print(f'Sent message: {message} by user {user_id} to group {self.event_id}')
        except json.JSONDecodeError as e:
            print(f'JSON decode error: {e}')
        except Exception as e:
            print(f'Error in receive method: {e}')
        

    async def chat_message(self, event):
        message = event.get('message')
        user_id = event.get('user_id')
        user_nickname = event.get('user_nickname')  
        user_first_name = event.get('user_first_name')
        user_last_name = event.get('user_last_name')
        timestamp = event.get('timestamp')
        
        # Check if the message sender is blocked by the receiver
        if await self.is_blocked_by_user(user_id):
            user_nickname = "Blocked User"
            message = "This message is blocked"

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'user_id': user_id,
            'user_nickname': user_nickname,
            'user_first_name': user_first_name,
            'user_last_name': user_last_name,
            'timestamp': timestamp
        }))
    
    @sync_to_async
    def is_blocked_by_user(self, sender_id):
        """Check if the connected user has blocked the sender."""
        from users.models import Block
        return Block.objects.filter(blocker=self.scope['user'], blocked_id=sender_id).exists()

    @sync_to_async
    def get_old_messages(self):
        from .models import ChatMessage
        from users.models import Block  # Import Block model to check blocked users

        # Get the list of users blocked by the current user
        blocked_users = Block.objects.filter(blocker=self.scope['user']).values_list('blocked', flat=True)
        
        # Fetch all messages for this event
        queryset = ChatMessage.objects.filter(event_id=self.event_id).order_by('timestamp')

        # Modify messages where the sender is in the blocked list
        messages = []
        for message in queryset:
            if message.user_id in blocked_users:
                # Replace content for blocked users
                messages.append({
                    'user_id': message.user_id,
                    'user_nickname': "Blocked user",
                    'message': "blocked",
                    'timestamp': message.timestamp.isoformat(),
                })
            else:
                # Otherwise, display the actual message content
                messages.append({
                    'user_id': message.user_id,
                    'user_nickname': message.user.nickname,  # Assuming nickname field
                    'message': message.message,
                    'timestamp': message.timestamp.isoformat(),
                })

        return messages

    @sync_to_async
    def save_message(self, user_id, message):
        from .models import ChatMessage  # Import model inside the method
        # Create a new chat message entry
        ChatMessage.objects.create(
            event_id=self.event_id,
            user_id=user_id,
            message=message,
            timestamp=timezone.now()
        )

    @sync_to_async
    def notify_users_about_event(self, sender_id, message):
        from .models import Event, Registration  # Import models inside the method
        # Fetch all users from the event
        registrations = Registration.objects.filter(event_id=self.event_id)
        users = [registration.user for registration in registrations]
        
        # Fetch the creator of the event
        event = Event.objects.get(id=self.event_id)
        creator = event.created_by
        
        # Add the creator to the list if not already included
        if creator not in users:
            users.append(creator)
        
        # Notify each user except the sender
        for user in users:
            if user.id != sender_id and user.is_active:
                notify_user_about_event(user, self.event_id, f"{event.name} - 新的聊天室通知", message)
'''
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
from asgiref.sync import sync_to_async

from .serializers import ChatMessageSerializer
from .views import notify_user_about_event

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.event_id = self.scope['url_route']['kwargs']['event_id']
        print(f'Successfully connected to event {self.event_id}')
        
        # Join the chat room group
        await self.channel_layer.group_add(
            self.event_id,
            self.channel_name
        )
        await self.accept()
        
        # Send old messages when a new user connects
        messages = await self.get_old_messages()
        for message in messages:
            await self.send(text_data=json.dumps(message))
        
    async def disconnect(self, close_code):
        # Leave the chat room group
        await self.channel_layer.group_discard(
            self.event_id,
            self.channel_name
        )
        print(f'Disconnected from event {self.event_id}')
    
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json.get('message')
            user_id = self.scope['user'].id
            
            print(f'Received message: {message} from user {user_id}')
            
            if not message:
                raise ValueError("Message content is empty or not provided")
            
            # Save the message to the database
            await self.save_message(user_id, message)
            await self.notify_users_about_event(user_id, message)
            
            # Broadcast message to the chat room group
            await self.channel_layer.group_send(
                self.event_id,
                {
                    'type': 'chat_message',
                    'message': message,
                    'user_id': user_id,
                    'user_nickname': self.scope['user'].nickname,
                    'user_first_name': self.scope['user'].first_name,
                    'user_last_name': self.scope['user'].last_name,
                    'timestamp': timezone.now().isoformat()
                }
            )
            
            print(f'Sent message: {message} by user {user_id} to group {self.event_id}')
        except json.JSONDecodeError as e:
            print(f'JSON decode error: {e}')
        except Exception as e:
            print(f'Error in receive method: {e}')
        

    async def chat_message(self, event):
        message = event.get('message')
        user_id = event.get('user_id')
        user_nickname = event.get('user_nickname')  
        user_first_name = event.get('user_first_name')
        user_last_name = event.get('user_last_name')
        timestamp = event.get('timestamp')

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'user_id': user_id,
            'user_nickname': user_nickname,
            'user_first_name': user_first_name,
            'user_last_name': user_last_name,
            'timestamp': timestamp
        }))
    @sync_to_async
    def get_old_messages(self):
        from .models import ChatMessage  # Import model inside the method
        # Serialize messages using ChatMessageSerializer
        queryset = ChatMessage.objects.filter(event_id=self.event_id).order_by('timestamp')
        serializer = ChatMessageSerializer(queryset, many=True)
        return serializer.data

    @sync_to_async
    def save_message(self, user_id, message):
        from .models import ChatMessage  # Import model inside the method
        # Create a new chat message entry
        ChatMessage.objects.create(
            event_id=self.event_id,
            user_id=user_id,
            message=message,
            timestamp=timezone.now()
        )

    @sync_to_async
    def notify_users_about_event(self, sender_id, message):
        from .models import Event, Registration  # Import models inside the method
        # Fetch all users from the event
        registrations = Registration.objects.filter(event_id=self.event_id)
        users = [registration.user for registration in registrations]
        
        # Fetch the creator of the event
        event = Event.objects.get(id=self.event_id)
        creator = event.created_by
        
        # Add the creator to the list if not already included
        if creator not in users:
            users.append(creator)
        
        # Notify each user except the sender
        for user in users:
            if user.id != sender_id and user.is_active:
                notify_user_about_event(user, self.event_id, f"{event.name} - 新的聊天室通知", message)
'''