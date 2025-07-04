"""
RPO Automation WebApp - á¤ó¢×ê±ü·çó
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import os
import logging

from .routers import requirements, results

# í°-š
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """¢×ê±ü·çóné¤Õµ¤¯ë¡"""
    logger.info("Starting RPO Automation WebApp...")
    yield
    logger.info("Shutting down RPO Automation WebApp...")

# FastAPI¢×ê±ü·çón\
app = FastAPI(
    title="RPO Automation System",
    description="¡(ãLmÙ’¹‡Y‹_nêÕ·¹Æà",
    version="1.0.0",
    lifespan=lifespan
)

# CORS-š
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ,j°ƒgoik-š
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIëü¿ün{2
app.include_router(requirements.router)
app.include_router(results.router)

# Y„Õ¡¤ëhÆó×ìüÈn-š
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")
templates = Jinja2Templates(directory="src/web/templates")

@app.get("/")
async def root(request: Request):
    """ëüÈÚü¸"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Øë¹Á§Ã¯¨óÉİ¤óÈ"""
    return {
        "status": "healthy",
        "service": "rpo-automation-webapp",
        "version": "1.0.0"
    }

@app.get("/api/info")
async def api_info():
    """APIÅ1¨óÉİ¤óÈ"""
    return {
        "title": "RPO Automation API",
        "version": "1.0.0",
        "endpoints": {
            "requirements": "/api/requirements",
            "results": "/api/results",
            "health": "/health"
        }
    }

# ¨éüÏóÉêó°
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """404¨éüÏóÉéü"""
    if request.url.path.startswith("/api/"):
        return {"error": "Endpoint not found", "status": 404}
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """500¨éüÏóÉéü"""
    logger.error(f"Internal server error: {exc}")
    if request.url.path.startswith("/api/"):
        return {"error": "Internal server error", "status": 500}
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("WEBAPP_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)