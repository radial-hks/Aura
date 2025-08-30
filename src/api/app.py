# Aura FastAPI应用主文件
# 配置API服务器、中间件、异常处理、CORS等

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time
import logging
import traceback
from typing import Dict, Any
import uvicorn

from .routes import api_router
from config.settings import get_config

# 获取配置
config = get_config()

# 创建限流器
limiter = Limiter(key_func=get_remote_address)

# 创建FastAPI应用
app = FastAPI(
    title="Aura智能浏览器自动化系统",
    description="通过自然语言指令操作浏览器的智能系统API",
    version="1.0.0",
    docs_url=None,  # 禁用默认文档
    redoc_url=None,  # 禁用默认ReDoc
    openapi_url="/api/v1/openapi.json" if config.api.enable_docs else None
)

# 添加限流器到应用
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.logging.level.upper()),
    format=config.logging.format
)
logger = logging.getLogger(__name__)

# ==================== 中间件配置 ====================

# CORS中间件
if config.api.enable_cors:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 受信任主机中间件
if config.api.trusted_hosts:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=config.api.trusted_hosts
    )

# 会话中间件
app.add_middleware(
    SessionMiddleware,
    secret_key=config.security.secret_key,
    max_age=config.security.session_timeout
)

# Gzip压缩中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    start_time = time.time()
    
    # 记录请求信息
    logger.info(f"Request: {request.method} {request.url}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # 记录响应信息
        logger.info(
            f"Response: {response.status_code} - {process_time:.3f}s"
        )
        
        # 添加响应头
        response.headers["X-Process-Time"] = str(process_time)
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Request failed: {request.method} {request.url} - "
            f"{process_time:.3f}s - {str(e)}"
        )
        raise

# 安全头中间件
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """添加安全响应头"""
    response = await call_next(request)
    
    # 安全头
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    if config.api.enable_https:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    
    return response

# ==================== 异常处理 ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "timestamp": time.time()
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    logger.error(f"Unhandled exception: {str(exc)}\n{traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "timestamp": time.time(),
                "detail": str(exc) if config.environment.name == "development" else None
            }
        }
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """值错误处理"""
    logger.warning(f"Value error: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": 400,
                "message": "Invalid input",
                "detail": str(exc),
                "timestamp": time.time()
            }
        }
    )

# ==================== 路由注册 ====================

# 注册API路由
app.include_router(api_router)

# ==================== 文档路由 ====================

if config.api.enable_docs:
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        """自定义Swagger UI"""
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=app.title + " - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        )
    
    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        """ReDoc文档"""
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=app.title + " - ReDoc",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js",
        )

# ==================== 根路由 ====================

@app.get("/")
@limiter.limit("60/minute")
async def root(request: Request):
    """根路径"""
    return {
        "name": "Aura智能浏览器自动化系统",
        "version": "1.0.0",
        "description": "通过自然语言指令操作浏览器的智能系统",
        "docs_url": "/docs" if config.api.enable_docs else None,
        "api_version": "v1",
        "status": "running"
    }

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """网站图标"""
    return JSONResponse(content={}, status_code=204)

# ==================== 自定义OpenAPI ====================

def custom_openapi():
    """自定义OpenAPI规范"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # 添加安全定义
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    # 添加全局安全要求
    openapi_schema["security"] = [{"BearerAuth": []}]
    
    # 添加服务器信息
    openapi_schema["servers"] = [
        {
            "url": f"http://localhost:{config.api.port}",
            "description": "开发服务器"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# ==================== 启动事件 ====================

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("Aura API服务启动中...")
    
    # 初始化数据库连接
    # TODO: 初始化数据库
    
    # 初始化Redis连接
    # TODO: 初始化Redis
    
    # 初始化其他服务
    # TODO: 初始化其他服务
    
    logger.info(f"Aura API服务已启动，监听端口: {config.api.port}")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("Aura API服务关闭中...")
    
    # 清理资源
    # TODO: 关闭数据库连接
    # TODO: 关闭Redis连接
    # TODO: 清理其他资源
    
    logger.info("Aura API服务已关闭")

# ==================== 运行配置 ====================

def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    return app

def run_server():
    """运行API服务器"""
    uvicorn.run(
        "src.api.app:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.environment.name == "development",
        log_level=config.logging.level.lower(),
        access_log=True,
        server_header=False,
        date_header=False
    )

if __name__ == "__main__":
    run_server()