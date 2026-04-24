import httpx
import json
from ken.config import config
from ken.memory import Memory

async def stream_chat(prompt: str, memory: Memory):
    """Yields tokens from the Ollama chat stream."""
    memory.add_user(prompt)
    
    # Prepend a lightweight system prompt
    system_msg = {
        "role": "system", 
        "content": "You are Ken, a concise, helpful Linux assistant. Give brief, direct answers."
    }
    
    payload = {
        "model": config.model,
        "messages": [system_msg] + memory.get_context(),
        "stream": True
    }
    
    full_response = ""
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", f"{config.ollama_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for chunk in response.aiter_lines():
                    if chunk:
                        try:
                            data = json.loads(chunk)
                            if "message" in data and "content" in data["message"]:
                                token = data["message"]["content"]
                                full_response += token
                                yield token
                        except json.JSONDecodeError:
                            continue
    except httpx.ConnectError:
        yield "\n[Error] Unable to connect to Ollama. Is it running?"
    except httpx.ReadTimeout:
        yield "\n[Error] Ollama timed out. The model might be loading or the system is under heavy load."
    except Exception as e:
        yield f"\n[Error] Unexpected error from LLM: {str(e)}"
        
    if full_response:
        memory.add_assistant(full_response)
