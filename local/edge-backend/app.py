from fastapi import FastAPI

from routes.access import router as access_router
from routes.auth import router as auth_router
from routes.chat import router as chat_router
from routes.health import router as health_router
from routes.jobs import router as jobs_router
from routes.media import router as media_router
from routes.session import router as session_router
from services.access_service import access_service
from services.db import ping_database
from services.observability import edge_observability
from services.job_manager import job_manager
from services.storage import redis_store

app = FastAPI(title="A22 Edge Backend", version="0.2.0")
app.include_router(health_router)
app.include_router(session_router)
app.include_router(access_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(jobs_router)
app.include_router(media_router)


@app.on_event("startup")
async def on_startup() -> None:
    redis_store.ping()
    ping_database()
    access_service.sync_invitation_codes()
    edge_observability.log_run_start()
    await job_manager.start()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await job_manager.stop()
    edge_observability.log_run_stop()
