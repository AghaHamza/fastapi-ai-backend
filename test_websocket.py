import asyncio
import websockets
import json

async def chat():
    uri = "ws://localhost:8000/ws/1"

    async with websockets.connect(uri) as ws:
        print("Connected! Type your message (or 'quit' to exit):")

        while True:
            user_input = input("You: ")
            if user_input.lower() == "quit":
                break

            # Send message
            await ws.send(json.dumps({"message": user_input}))

            # Receive responses
            while True:
                response = await ws.recv()
                data = json.loads(response)

                if data["type"] == "typing":
                    print("AI is thinking...")
                elif data["type"] == "message":
                    print(f"AI: {data['content']}")
                    print(f"(tokens used: {data['tokens']})")
                    break

asyncio.run(chat())