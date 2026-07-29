import httpx
import asyncio

async def test_stream():
    token = ""
    
    async with httpx.AsyncClient(timeout=30) as client:
        async with client.stream(
            "POST",
            "http://localhost:8000/ai/chat/stream",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={"message": "Tell me about Python in 5 sentences"}
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]  # remove "data: " prefix
                    if data == "[DONE]":
                        print("\n--- Stream complete ---")
                        break
                    chunk = json.loads(data)
                    print(chunk["chunk"], end="", flush=True)

import json
asyncio.run(test_stream())