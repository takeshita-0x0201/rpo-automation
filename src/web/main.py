"""
RPO Automation WebApp - ��������
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import os
import logging

from .routers import requirements, results

# �-�
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """�������n�յ���"""
    logger.info("Starting RPO Automation WebApp...")
    yield
    logger.info("Shutting down RPO Automation WebApp...")

# FastAPI�������n\
app = FastAPI(
    title="RPO Automation System",
    description="�(�Lmْ��Y�_�n������",
    version="1.0.0",
    lifespan=lifespan
)

# CORS-�
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ,j��goik-�
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API����n{2
app.include_router(requirements.router)
app.include_router(results.router)

# Y�ա��h������n-�
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")
templates = Jinja2Templates(directory="src/web/templates")

@app.get("/")
async def root(request: Request):
    """������"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """����ï���ݤ��"""
    return {
        "status": "healthy",
        "service": "rpo-automation-webapp",
        "version": "1.0.0"
    }

@app.get("/api/info")
async def api_info():
    """API�1���ݤ��"""
    return {
        "title": "RPO Automation API",
        "version": "1.0.0",
        "endpoints": {
            "requirements": "/api/requirements",
            "results": "/api/results",
            "health": "/health"
        }
    }

# ��������
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """404��������"""
    if request.url.path.startswith("/api/"):
        return {"error": "Endpoint not found", "status": 404}
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """500��������"""
    logger.error(f"Internal server error: {exc}")
    if request.url.path.startswith("/api/"):
        return {"error": "Internal server error", "status": 500}
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("WEBAPP_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)