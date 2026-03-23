from fastapi import FastAPI

from routes.chat import router as chat_router
from routes.health import router as health_router

app = FastAPI(title="A22 Edge Backend", version="0.2.0")
app.include_router(health_router)
app.include_router(chat_router)
