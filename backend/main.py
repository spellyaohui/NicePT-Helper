"""NicePT Helper - 应用入口"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db
from services.scheduler import init_scheduler, shutdown_scheduler, restore_expiry_jobs, restore_interval_jobs

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("NicePT Helper 启动中...")
    await init_db()
    init_scheduler()
    # 恢复所有未过期种子的精确到期定时任务
    await restore_expiry_jobs()
    # 恢复所有“间隔型（interval）”任务（自动下载/账号刷新/状态同步/过期检查/动态删种/失效检查等）
    # 注意：每个种子“促销到期”的精确任务不在这里注册，由 restore_expiry_jobs() 负责。
    await restore_interval_jobs()
    logger.info("NicePT Helper 启动完成")
    yield
    shutdown_scheduler()
    logger.info("NicePT Helper 已关闭")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
from routers import auth, accounts, torrents, rules, downloaders, history, settings as settings_router, site_login, dashboard, logs, hr

app.include_router(auth.router, prefix="/api")
app.include_router(accounts.router, prefix="/api")
app.include_router(torrents.router, prefix="/api")
app.include_router(rules.router, prefix="/api")
app.include_router(downloaders.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
app.include_router(site_login.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(hr.router, prefix="/api")


# 挂载静态文件（测试页面）
from fastapi.staticfiles import StaticFiles
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
