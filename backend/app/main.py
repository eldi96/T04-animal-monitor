import asyncio
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.routes import router
from app.services.scheduler import run_daily_collection


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.getenv("T04_ENABLE_SCHEDULER", "false").lower() != "true":
        yield
        return
    scheduler = asyncio.create_task(run_daily_collection(), name="daily-animal-notice-collection")
    try:
        yield
    finally:
        scheduler.cancel()
        try:
            await scheduler
        except asyncio.CancelledError:
            pass


app = FastAPI(title="T04 데이터 신뢰성 API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(router)


@app.get("/healthz")
def health():
    return {"status": "ok"}


# Enable the built frontend only when explicitly configured by the deployment.
static_dir = os.getenv("T04_STATIC_DIR")
if static_dir:
    frontend_root = Path(static_dir).resolve()
    if not (frontend_root / "index.html").is_file():
        raise RuntimeError("T04_STATIC_DIR must contain the built frontend index.html")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API not found")
        target = (frontend_root / path).resolve()
        if not target.is_relative_to(frontend_root):
            raise HTTPException(status_code=404)
        if target.is_file():
            return FileResponse(target)
        if Path(path).suffix:
            raise HTTPException(status_code=404)
        return FileResponse(frontend_root / "index.html")
