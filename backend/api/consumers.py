import json
from channels.generic.websocket import AsyncWebsocketConsumer

class VideoJobConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.job_id = self.scope['url_route']['kwargs']['job_id']
        self.room_group_name = f'job_{self.job_id}'

        # Join the unique room for this job
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave the room
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # This method handles the 'job_update' message sent from tasks.py
    async def job_update(self, event):
        data = event['data']
        # Send the status/progress/outputs to the React frontend
        await self.send(text_data=json.dumps(data))