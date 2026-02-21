"""系统设置路由"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import SystemSetting
from utils.auth import get_current_user
from services.scheduler import (
    get_scheduler_status, scheduler, add_job, remove_job,
    auto_download_torrents, refresh_all_accounts,
    sync_download_status, check_expired_torrents,
    check_dynamic_delete, check_unregistered_torrents,
)

router = APIRouter(prefix="/settings", tags=["系统设置"], dependencies=[Depends(get_current_user)])


class SettingUpdate(BaseModel):
    value: Any


# ========== 通用设置 ==========

@router.get("/")
async def list_settings(db: AsyncSession = Depends(get_db)):
    """获取所有设置"""
    result = await db.execute(select(SystemSetting))
    settings = result.scalars().all()
    return {s.key: s.value for s in settings}


@router.get("/scheduler-status")
async def scheduler_status():
    """获取调度器状态"""
    return get_scheduler_status()


@router.get("/kv/{key}")
async def get_setting(key: str, db: AsyncSession = Depends(get_db)):
    """获取单个设置"""
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="设置不存在")
    return {"key": setting.key, "value": setting.value}


@router.put("/kv/{key}")
async def update_setting(key: str, req: SettingUpdate, db: AsyncSession = Depends(get_db)):
    """更新设置"""
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = req.value
    else:
        setting = SystemSetting(key=key, value=req.value)
        db.add(setting)
    await db.commit()
    return {"key": key, "value": req.value}


@router.delete("/kv/{key}")
async def delete_setting(key: str, db: AsyncSession = Depends(get_db)):
    """删除设置"""
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="设置不存在")
    await db.delete(setting)
    await db.commit()
    return {"message": "设置已删除"}


# ========== 自动删种设置 ==========

DEFAULT_AUTO_DELETE = {
    "enabled": False,

    # 促销过期处理
    "delete_expired": True,           # 促销过期处理总开关
    "expired_action": "delete",      # delete=删除 / pause=暂停，默认删除

    # 下载中的非免费处理
    "delete_non_free": False,         # 非免费删种

    # 动态容量删种
    "dynamic_delete_enabled": False,  # 动态容量删种
    "disk_max_gb": 10000,             # 已用空间触发上限（GB）
    "disk_target_gb": 8000,           # 已用空间目标值（GB）

    # 失效种子处理
    "delete_unregistered": True,      # 删除站点已下架种子

    # 兼容旧字段
    "disk_threshold_gb": 100,         # 旧字段：磁盘剩余阈值（GB）
}


@router.get("/auto-delete")
async def get_auto_delete(db: AsyncSession = Depends(get_db)):
    """获取自动删种设置"""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "auto_delete")
    )
    setting = result.scalar_one_or_none()
    value = setting.value if (setting and setting.value) else {}

    # 兜底补全新字段，避免前端拿到旧结构导致表单字段缺失
    merged = {**DEFAULT_AUTO_DELETE, **value}
    return merged


@router.put("/auto-delete")
async def update_auto_delete(req: SettingUpdate, db: AsyncSession = Depends(get_db)):
    """更新自动删种设置"""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "auto_delete")
    )
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = req.value
    else:
        setting = SystemSetting(key="auto_delete", value=req.value)
        db.add(setting)
    await db.commit()

    # 关键：重新开启自动删种/到期处理时，需要恢复“每个种子一个定时器”的精确到期任务。
    # 注意：如果主开关仍关闭，定时器触发后也会在处理函数内直接跳过。
    try:
        from services.scheduler import restore_expiry_jobs
        await restore_expiry_jobs()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"恢复精确到期定时器失败: {e}")

    return {"key": "auto_delete", "value": req.value}


# ========== 刷新间隔设置 ==========

DEFAULT_INTERVALS = {
    "auto_download_minutes": 10,         # 自动下载间隔（分钟）
    "account_refresh_minutes": 60,       # 账号刷新间隔（分钟）
    "status_sync_minutes": 5,            # 状态同步间隔（分钟）
    "expired_check_minutes": 30,         # 过期检查间隔（分钟）
    "dynamic_delete_minutes": 10,        # 动态删种间隔（分钟）
    "unregistered_check_minutes": 10,    # 失效种子检查间隔（分钟）
}


@router.get("/refresh-intervals")
async def get_refresh_intervals(db: AsyncSession = Depends(get_db)):
    """获取刷新间隔设置"""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "refresh_intervals")
    )
    setting = result.scalar_one_or_none()
    value = setting.value if (setting and setting.value) else {}
    return {**DEFAULT_INTERVALS, **value}


@router.put("/refresh-intervals")
async def update_refresh_intervals(req: SettingUpdate, db: AsyncSession = Depends(get_db)):
    """更新刷新间隔并重新注册定时任务"""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "refresh_intervals")
    )
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = req.value
    else:
        setting = SystemSetting(key="refresh_intervals", value=req.value)
        db.add(setting)
    await db.commit()

    # 重新注册定时任务
    _register_scheduled_jobs(req.value)

    return {"key": "refresh_intervals", "value": req.value}


# ========== 调度控制 ==========

DEFAULT_SCHEDULE_CONTROL = {
    "auto_download_enabled": False,
    "account_refresh_enabled": False,
    "status_sync_enabled": False,
    "expired_check_enabled": False,
    "dynamic_delete_enabled": False,
    "unregistered_check_enabled": False,
}


@router.get("/schedule-control")
async def get_schedule_control(db: AsyncSession = Depends(get_db)):
    """获取调度任务开关"""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "schedule_control")
    )
    setting = result.scalar_one_or_none()
    value = setting.value if (setting and setting.value) else {}
    return {**DEFAULT_SCHEDULE_CONTROL, **value}


@router.put("/schedule-control")
async def update_schedule_control(req: SettingUpdate, db: AsyncSession = Depends(get_db)):
    """更新调度任务开关"""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "schedule_control")
    )
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = req.value
    else:
        setting = SystemSetting(key="schedule_control", value=req.value)
        db.add(setting)
    await db.commit()

    # 获取间隔设置
    interval_result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "refresh_intervals")
    )
    interval_setting = interval_result.scalar_one_or_none()
    intervals = interval_setting.value if interval_setting and interval_setting.value else DEFAULT_INTERVALS

    # 根据开关注册/移除任务
    control = req.value

    if control.get("auto_download_enabled"):
        add_job(auto_download_torrents, "interval",
                "auto_download", minutes=intervals.get("auto_download_minutes", 10), name="自动下载")
    else:
        remove_job("auto_download")

    if control.get("account_refresh_enabled"):
        add_job(refresh_all_accounts, "interval",
                "account_refresh", minutes=intervals.get("account_refresh_minutes", 60), name="账号刷新")
    else:
        remove_job("account_refresh")

    if control.get("status_sync_enabled"):
        add_job(sync_download_status, "interval",
                "status_sync", minutes=intervals.get("status_sync_minutes", 5), name="状态同步")
    else:
        remove_job("status_sync")

    if control.get("expired_check_enabled"):
        add_job(check_expired_torrents, "interval",
                "expired_check", minutes=intervals.get("expired_check_minutes", 30), name="过期检查（兜底）")
    else:
        remove_job("expired_check")

    if control.get("dynamic_delete_enabled"):
        add_job(check_dynamic_delete, "interval",
                "dynamic_delete", minutes=intervals.get("dynamic_delete_minutes", 10), name="动态删种")
    else:
        remove_job("dynamic_delete")

    if control.get("unregistered_check_enabled"):
        add_job(check_unregistered_torrents, "interval",
                "unregistered_check", minutes=intervals.get("unregistered_check_minutes", 10), name="失效种子检查")
    else:
        remove_job("unregistered_check")

    # 关键：当用户重新开启相关任务时，需要确保“下载中的种子”每个种子对应的精确到期定时器已恢复。
    # 这里不强依赖 expired_check_enabled，因为精确定时器才是主策略（interval 仅兜底）。
    try:
        from services.scheduler import restore_expiry_jobs
        await restore_expiry_jobs()
    except Exception as e:
        # 不阻塞设置保存，但会在日志中提示
        import logging
        logging.getLogger(__name__).error(f"恢复精确到期定时器失败: {e}")

    return {"key": "schedule_control", "value": req.value}


@router.post("/restart-scheduler")
async def restart_scheduler():
    """重启调度器（会自动恢复所有任务）"""
    from services.scheduler import (
        shutdown_scheduler, init_scheduler,
        restore_expiry_jobs, restore_interval_jobs,
    )

    shutdown_scheduler()
    init_scheduler()

    # 关键：恢复“每个种子一个定时器”的促销到期精确任务（避免错过免费到期时间点）
    await restore_expiry_jobs()

    # 恢复所有 interval 型任务（自动下载/账号刷新/状态同步/过期检查/动态删种/失效检查等）
    await restore_interval_jobs()

    return {"message": "调度器已重启", "status": get_scheduler_status()}


def _register_scheduled_jobs(intervals: dict):
    """根据间隔设置重新注册所有已启用的任务"""
    for job in scheduler.get_jobs():
        job_id = job.id
        if job_id == "auto_download":
            add_job(auto_download_torrents, "interval",
                    "auto_download", minutes=intervals.get("auto_download_minutes", 10), name="自动下载")
        elif job_id == "account_refresh":
            add_job(refresh_all_accounts, "interval",
                    "account_refresh", minutes=intervals.get("account_refresh_minutes", 60), name="账号刷新")
        elif job_id == "status_sync":
            add_job(sync_download_status, "interval",
                    "status_sync", minutes=intervals.get("status_sync_minutes", 5), name="状态同步")
        elif job_id == "expired_check":
            add_job(check_expired_torrents, "interval",
                    "expired_check", minutes=intervals.get("expired_check_minutes", 30), name="过期检查（兜底）")
        elif job_id == "dynamic_delete":
            add_job(check_dynamic_delete, "interval",
                    "dynamic_delete", minutes=intervals.get("dynamic_delete_minutes", 10), name="动态删种")
        elif job_id == "unregistered_check":
            add_job(check_unregistered_torrents, "interval",
                    "unregistered_check", minutes=intervals.get("unregistered_check_minutes", 10), name="失效种子检查")
