# Aura API路由定义
# 提供RESTful API接口，支持任务管理、技能库操作、站点模型查询等功能

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import json
import uuid

from ..core.orchestrator import Orchestrator, JobRequest, JobStatus
from ..modules.skill_library import SkillLibrary, SkillManifest
from ..modules.site_explorer import SiteExplorer, SiteModel
from ..modules.command_parser import CommandParser, ParsedCommand
from ..core.policy_engine import PolicyEngine
from ..core.risk_engine import RiskEngine
from config.settings import get_config

# 创建路由器
api_router = APIRouter(prefix="/api/v1")
security = HTTPBearer()
config = get_config()

# WebSocket连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.job_subscribers: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        # 从所有订阅中移除
        for job_id, subscribers in self.job_subscribers.items():
            if websocket in subscribers:
                subscribers.remove(websocket)
    
    async def subscribe_to_job(self, websocket: WebSocket, job_id: str):
        if job_id not in self.job_subscribers:
            self.job_subscribers[job_id] = []
        self.job_subscribers[job_id].append(websocket)
    
    async def broadcast_job_update(self, job_id: str, message: dict):
        if job_id in self.job_subscribers:
            for websocket in self.job_subscribers[job_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    # 连接已断开，移除
                    self.job_subscribers[job_id].remove(websocket)

manager = ConnectionManager()

# 依赖注入
async def get_orchestrator() -> Orchestrator:
    """获取Orchestrator实例"""
    return Orchestrator()

async def get_skill_library() -> SkillLibrary:
    """获取SkillLibrary实例"""
    return SkillLibrary()

async def get_site_explorer() -> SiteExplorer:
    """获取SiteExplorer实例"""
    return SiteExplorer()

async def get_command_parser() -> CommandParser:
    """获取CommandParser实例"""
    return CommandParser()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """验证JWT令牌"""
    # TODO: 实现JWT验证逻辑
    if not credentials.credentials:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return credentials.credentials

# ==================== 任务管理API ====================

@api_router.post("/jobs", response_model=dict)
async def create_job(
    request: JobRequest,
    background_tasks: BackgroundTasks,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    token: str = Depends(verify_token)
):
    """创建新的执行任务"""
    try:
        job = await orchestrator.create_job(request)
        
        # 在后台执行任务
        background_tasks.add_task(execute_job_background, job.id, orchestrator)
        
        return {
            "id": job.id,
            "status": job.status.value,
            "created_at": job.created_at.isoformat(),
            "estimated_duration": job.estimated_duration
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/jobs/{job_id}", response_model=dict)
async def get_job_status(
    job_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    token: str = Depends(verify_token)
):
    """查询任务状态"""
    try:
        job = await orchestrator.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "id": job.id,
            "status": job.status.value,
            "progress": job.progress,
            "result": job.result,
            "error": job.error,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            "execution_log": job.execution_log[-10:] if job.execution_log else []  # 最近10条日志
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/jobs/{job_id}/replay", response_model=dict)
async def replay_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    token: str = Depends(verify_token)
):
    """回放任务"""
    try:
        new_job = await orchestrator.replay_job(job_id)
        
        # 在后台执行回放任务
        background_tasks.add_task(execute_job_background, new_job.id, orchestrator)
        
        return {
            "id": new_job.id,
            "original_job_id": job_id,
            "status": new_job.status.value,
            "created_at": new_job.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.delete("/jobs/{job_id}")
async def cancel_job(
    job_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    token: str = Depends(verify_token)
):
    """取消任务"""
    try:
        success = await orchestrator.cancel_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
        
        return {"message": "Job cancelled successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/jobs", response_model=dict)
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    token: str = Depends(verify_token)
):
    """列出任务"""
    try:
        jobs = await orchestrator.list_jobs(
            status=JobStatus(status) if status else None,
            limit=limit,
            offset=offset
        )
        
        return {
            "jobs": [
                {
                    "id": job.id,
                    "status": job.status.value,
                    "progress": job.progress,
                    "created_at": job.created_at.isoformat(),
                    "updated_at": job.updated_at.isoformat() if job.updated_at else None
                }
                for job in jobs
            ],
            "total": len(jobs),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 技能库API ====================

@api_router.post("/skills/publish", response_model=dict)
async def publish_skill(
    manifest: SkillManifest,
    skill_library: SkillLibrary = Depends(get_skill_library),
    token: str = Depends(verify_token)
):
    """发布技能"""
    try:
        skill_id = await skill_library.register_skill(manifest)
        return {
            "skill_id": skill_id,
            "message": "Skill published successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/skills/{skill_id}", response_model=dict)
async def get_skill_details(
    skill_id: str,
    skill_library: SkillLibrary = Depends(get_skill_library),
    token: str = Depends(verify_token)
):
    """查询技能详情"""
    try:
        skill = await skill_library.get_skill_details(skill_id)
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        
        return skill.__dict__
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/skills/search", response_model=dict)
async def search_skills(
    query: Optional[str] = None,
    domain: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20,
    skill_library: SkillLibrary = Depends(get_skill_library),
    token: str = Depends(verify_token)
):
    """搜索技能"""
    try:
        skills = await skill_library.find_skills(
            query=query,
            domain=domain,
            category=category,
            limit=limit
        )
        
        return {
            "skills": [
                {
                    "id": skill.id,
                    "name": skill.name,
                    "description": skill.description,
                    "version": skill.version,
                    "target_domains": skill.target_domains,
                    "category": skill.category,
                    "rating": skill.rating,
                    "usage_count": skill.usage_count
                }
                for skill in skills
            ],
            "total": len(skills)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/skills/{skill_id}", response_model=dict)
async def update_skill(
    skill_id: str,
    manifest: SkillManifest,
    skill_library: SkillLibrary = Depends(get_skill_library),
    token: str = Depends(verify_token)
):
    """更新技能"""
    try:
        success = await skill_library.update_skill(skill_id, manifest)
        if not success:
            raise HTTPException(status_code=404, detail="Skill not found")
        
        return {"message": "Skill updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== 站点模型API ====================

@api_router.post("/models/update", response_model=dict)
async def update_site_model(
    domain: str,
    model_data: dict,
    site_explorer: SiteExplorer = Depends(get_site_explorer),
    token: str = Depends(verify_token)
):
    """更新站点模型"""
    try:
        version = await site_explorer.update_site_model(domain, model_data)
        return {
            "domain": domain,
            "version": version,
            "message": "Site model updated successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/models/{domain}", response_model=dict)
async def get_site_model(
    domain: str,
    version: Optional[str] = None,
    site_explorer: SiteExplorer = Depends(get_site_explorer),
    token: str = Depends(verify_token)
):
    """获取站点模型"""
    try:
        model = await site_explorer.get_site_model(domain, version)
        if not model:
            raise HTTPException(status_code=404, detail="Site model not found")
        
        return model.__dict__
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/models/search", response_model=dict)
async def search_site_models(
    query: Optional[str] = None,
    limit: int = 20,
    site_explorer: SiteExplorer = Depends(get_site_explorer),
    token: str = Depends(verify_token)
):
    """搜索站点模型"""
    try:
        models = await site_explorer.search_site_models(query, limit)
        
        return {
            "models": [
                {
                    "domain": model.domain,
                    "version": model.version,
                    "last_updated": model.last_updated.isoformat(),
                    "page_count": len(model.pages),
                    "confidence": model.confidence
                }
                for model in models
            ],
            "total": len(models)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 指令解析API ====================

@api_router.post("/commands/parse", response_model=dict)
async def parse_command(
    command: str,
    context: Optional[dict] = None,
    command_parser: CommandParser = Depends(get_command_parser),
    token: str = Depends(verify_token)
):
    """解析自然语言指令"""
    try:
        parsed = await command_parser.parse_command(command, context)
        
        return {
            "original_command": command,
            "parsed_intent": parsed.intent.value,
            "confidence": parsed.confidence,
            "parameters": parsed.parameters,
            "execution_strategy": parsed.execution_strategy.__dict__,
            "estimated_tokens": parsed.estimated_tokens,
            "risk_assessment": parsed.risk_assessment.__dict__
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== WebSocket API ====================

@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接端点"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "subscribe_job":
                job_id = message.get("job_id")
                if job_id:
                    await manager.subscribe_to_job(websocket, job_id)
                    await websocket.send_text(json.dumps({
                        "type": "subscription_confirmed",
                        "job_id": job_id
                    }))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ==================== 健康检查API ====================

@api_router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@api_router.get("/metrics")
async def get_metrics(
    orchestrator: Orchestrator = Depends(get_orchestrator),
    token: str = Depends(verify_token)
):
    """获取系统指标"""
    try:
        metrics = await orchestrator.get_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 后台任务 ====================

async def execute_job_background(job_id: str, orchestrator: Orchestrator):
    """后台执行任务"""
    try:
        async for update in orchestrator.execute_job(job_id):
            # 通过WebSocket广播任务更新
            await manager.broadcast_job_update(job_id, {
                "type": "job_update",
                "job_id": job_id,
                "status": update.get("status"),
                "progress": update.get("progress"),
                "message": update.get("message")
            })
    except Exception as e:
        # 广播错误信息
        await manager.broadcast_job_update(job_id, {
            "type": "job_error",
            "job_id": job_id,
            "error": str(e)
        })