from fastapi import FastAPI
from pydantic import BaseModel
import os

app = FastAPI()

class ChatRequest(BaseModel):
    text: str

@app.get("/health")
def health():
    return {
        "status": "ok",
        "cloud_api_base": os.getenv("CLOUD_API_BASE", "")
    }

@app.post("/chat")
def chat(req: ChatRequest):
    return {
        "reply_text": f"edge-backend received: {req.text}",
        "avatar_action": {
            "facial_expression": "neutral",
            "head_motion": "none"
        }
    }
