"""
FastAPI Main Application
Migrated from Flask app.py
"""

import os
import sys
import uuid
import logging
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_version():
    """Read version from VERSION file"""
    VERSION_FILE = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "VERSION"
    )
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r") as f:
            return f.read().strip() or "2.6.0"
    return "2.6.0"


VERSION = get_version()

# Load config
config = get_config()

# Initialize database
from db import database_pg as db
db.init_db()

# Create FastAPI app
app = FastAPI(
    title="Fund Daily API",
    description="基金每日分析系统 API",
    version=VERSION,
    docs_url="/docs" if config.app.env != "production" else None,
    redoc_url="/redoc" if config.app.env != "production" else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and add request ID"""
    request_id = str(uuid.uuid4())[:8]
    start_time = datetime.now()
    
    # Log request
    method = request.method
    path = request.path
    if '/password' in path or '/login' in path:
        logger.info(f"[{request_id}] {method} {path}")
    else:
        logger.info(f"[{request_id}] {method} {path}")
    
    # Process request
    response = await call_next(request)
    
    # Add headers
    response.headers['X-Request-ID'] = request_id
    
    # Add processing time
    duration = (datetime.now() - start_time).total_seconds()
    response.headers['X-Process-Time'] = f"{duration:.3f}"
    
    return response


# Error handlers
from web.api_fastapi.middleware.error_handler import (
    http_exception_handler,
    generic_exception_handler,
    APIException,
)

app.add_exception_handler(APIException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


# ---- Startup / Shutdown Events ----

@app.on_event("startup")
async def startup_event():
    """Start the scheduler when the FastAPI app starts"""
    # Only start scheduler if not running as a standalone scheduler service
    if os.getenv("SCHEDULER_STANDALONE") != "true":
        try:
            from src.scheduler.manager import get_scheduler_manager
            mgr = get_scheduler_manager()
            if not mgr.is_running():
                mgr.start()
                logger.info("✅ [FastAPI] Scheduler started on app startup")
        except Exception as e:
            logger.warning(f"⚠️ [FastAPI] Failed to start scheduler on startup: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the scheduler when the FastAPI app stops"""
    if os.getenv("SCHEDULER_STANDALONE") != "true":
        try:
            from src.scheduler.manager import get_scheduler_manager
            mgr = get_scheduler_manager()
            if mgr.is_running():
                mgr.stop()
                logger.info("⏹️ [FastAPI] Scheduler stopped on app shutdown")
        except Exception as e:
            logger.warning(f"⚠️ [FastAPI] Failed to stop scheduler on shutdown: {e}")


# Include routers
from web.api_fastapi.routers import auth, funds, holdings, analysis, quant, system, external, health, tasks, scheduler

app.include_router(auth.router)
app.include_router(funds.router)
app.include_router(holdings.router)
app.include_router(analysis.router)
app.include_router(quant.router)
app.include_router(system.router)
app.include_router(external.router)
app.include_router(health.router)
app.include_router(tasks.router)
app.include_router(tasks.fund_router)
app.include_router(scheduler.router)


@app.get("/export", tags=["系统"])
async def export_holdings(request: Request):
    """Export holdings as CSV"""
    import csv
    import io
    from datetime import datetime
    
    user_id = _get_user_id(request)
    if not user_id:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "请先登录"}
        )

    holdings = db.get_holdings(user_id)
    if not holdings:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "暂无持仓数据"}
        )

    export_data = []
    for h in holdings:
        code = h.get("code")
        from src.fetcher import fetch_fund_data
        fund_data = fetch_fund_data(code)
        from src.advice import get_fund_detail_info
        detail = get_fund_detail_info(code) if code else {}
        
        export_data.append({
            "code": code,
            "name": detail.get("fund_name", h.get("name", "")),
            "amount": h.get("amount", 0),
            "buy_nav": h.get("buy_nav", ""),
            "buy_date": h.get("buy_date", ""),
            "nav": detail.get("nav", ""),
            "daily_change": detail.get("daily_change", 0),
        })

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["code", "name", "amount", "buy_nav", "buy_date", "nav", "daily_change"])
    writer.writeheader()
    writer.writerows(export_data)
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8-sig",
        headers={
            "Content-Disposition": f"attachment; filename=holdings_{datetime.now().strftime('%Y%m%d')}.csv"
        }
    )


# Vue app routes - serve static files
DIST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "../dist")


@app.get("/")
async def serve_vue_app():
    """Serve Vue app"""
    index_path = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(
            index_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return {"message": "Vue app not built yet"}


@app.get("/{path:path}")
async def serve_static(path: str):
    """Serve Vue static files"""
    # Skip API routes
    if path.startswith("api/"):
        return JSONResponse(
            status_code=404,
            content={"error": "Not found"}
        )
    
    # Handle assets with compression support
    if path.startswith("assets/"):
        rel_path = path[len("assets/"):]
        static_dir = os.path.abspath(os.path.join(DIST_DIR, "assets"))
        
        # Priority: Brotli (.br) > Gzip (.gz) > original
        for ext, encoding in [('.br', 'br'), ('.gz', 'gzip'), ('', None)]:
            file_path = os.path.join(static_dir, rel_path + ext)
            if os.path.isfile(file_path):
                with open(file_path, 'rb') as f:
                    data = f.read()
                
                response = Response(
                    content=data,
                    headers={
                        "Cache-Control": "public, max-age=31536000, immutable",
                        "Content-Length": str(len(data))
                    }
                )
                if encoding:
                    response.headers["Content-Encoding"] = encoding
                    response.headers["Vary"] = "Accept-Encoding"
                    response.headers.pop("Content-Length", None)
                
                # Set content type
                import mimetypes
                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type:
                    response.headers["Content-Type"] = mime_type
                elif rel_path.endswith('.js'):
                    response.headers["Content-Type"] = "text/javascript"
                elif rel_path.endswith('.css'):
                    response.headers["Content-Type"] = "text/css"
                
                return response
        
        return JSONResponse(status_code=404, content={"error": "Not found"})
    
    # SPA fallback - serve index.html
    index_path = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(
            index_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    
    return JSONResponse(status_code=404, content={"error": "Not found"})


# Helper function
def _get_user_id(request: Request) -> str:
    """Get user_id from JWT token or session cookie"""
    from src.jwt_auth import verify_access_token
    
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        is_valid, payload, _ = verify_access_token(token)
        if is_valid:
            return payload.get("sub")
    
    return request.cookies.get("session")


# Import json for config operations
import json


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host=config.server.host,
        port=config.server.port,
        log_level="info"
    )
