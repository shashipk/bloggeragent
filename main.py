import os
import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from google.adk.runners import InMemoryRunner
from google.genai import types

# Import the root agent
try:
    from bloggeragent.agent import root_agent
except ImportError:
    from agent import root_agent

app = FastAPI(title="ADK Blogger Agent Chat UI")

# Mount the static directory if it exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_session"
    user_id: str = "default_user"

async def event_generator(message: str, session_id: str, user_id: str):
    runner = InMemoryRunner(agent=root_agent)
    runner.auto_create_session = True
    
    user_msg = types.Content(
        role="user",
        parts=[types.Part(text=message)]
    )
    
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_msg
        ):
            # Extract relevant fields from the event to send to the UI
            author = event.author or "Agent"
            text_content = ""
            
            if event.content and event.content.parts:
                text_content = "".join(part.text for part in event.content.parts if part.text)
            
            data = {
                "event_id": event.id,
                "author": author,
                "text": text_content,
                "output": event.output,
                "partial": event.partial,
                "error_message": event.error_message,
                "node_path": event.node_info.path if event.node_info else None
            }
            yield f"data: {json.dumps(data)}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error_message': str(e)})}\n\n"

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    return StreamingResponse(
        event_generator(request.message, request.session_id, request.user_id),
        media_type="text/event-stream"
    )

@app.get("/")
async def get_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    return HTMLResponse(content="<h1>Chat UI index.html not found</h1>", status_code=404)

if __name__ == "__main__":
    import uvicorn
    # Use PORT env variable for Cloud Run compatibility
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
