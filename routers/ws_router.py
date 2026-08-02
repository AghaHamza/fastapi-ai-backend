from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel
from groq import AsyncGroq
import os
import json

router = APIRouter(tags=["WebSocket"])

client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

# Connection manager — tracks all active connections
class ConnectionManager:
    def __init__(self):
        # user_id → WebSocket connection
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"User {user_id} connected. Total: {len(self.active_connections)}")

    def disconnect(self, user_id: int):
        self.active_connections.pop(user_id, None)
        print(f"User {user_id} disconnected.")

    async def send(self, user_id: int, message: dict):
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_json(message)

    async def broadcast(self, message: dict):
        for ws in self.active_connections.values():
            await ws.send_json(message)

manager = ConnectionManager()

# WebSocket endpoint
@router.websocket("/ws/{user_id}")
async def websocket_chat(websocket: WebSocket, user_id: int):
    await manager.connect(user_id, websocket)

    try:
        while True:
            # Wait for message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            user_message = message.get("message", "")

            # Send "typing" indicator
            await manager.send(user_id, {"type": "typing", "content": "..."})

            # Call Groq
            response = await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": user_message}
                ]
            )

            ai_response = response.choices[0].message.content

            # Send AI response back
            await manager.send(user_id, {
                "type": "message",
                "content": ai_response,
                "tokens": response.usage.total_tokens
            })

    except WebSocketDisconnect:
        manager.disconnect(user_id)

class BroadcastMessage(BaseModel):
    message: str

@router.post("/ws/broadcast")
async def broadcast(body: BroadcastMessage):
    await manager.broadcast({
        "type": "broadcast",
        "content": body.message
    })
    return {"message": "Broadcasted to all users"}