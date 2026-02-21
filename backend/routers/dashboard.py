"""仪表盘路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Account, DownloadHistory, Downloader, FilterRule
from utils.auth import get_current_user
from services.downloader import create_downloader

router = APIRouter(prefix="/dashboard", tags=["仪表盘"], dependencies=[Depends(get_current_user)])


@router.get("/")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    """获取仪表盘汇总数据"""
    # 账号数
    acc_count = (await db.execute(select(func.count()).select_from(Account))).scalar() or 0

    # 规则数
    rule_count = (await db.execute(select(func.count()).select_from(FilterRule))).scalar() or 0
    enabled_rules = (await db.execute(
        select(func.count()).select_from(FilterRule).where(FilterRule.enabled == True)
    )).scalar() or 0

    # 下载器数
    dl_count = (await db.execute(select(func.count()).select_from(Downloader))).scalar() or 0

    # 历史统计
    total_history = (await db.execute(
        select(func.count()).select_from(DownloadHistory)
    )).scalar() or 0
    downloading = (await db.execute(
        select(func.count()).select_from(DownloadHistory).where(DownloadHistory.status == "downloading")
    )).scalar() or 0
    seeding = (await db.execute(
        select(func.count()).select_from(DownloadHistory).where(DownloadHistory.status == "seeding")
    )).scalar() or 0

    # 最近下载
    recent_result = await db.execute(
        select(DownloadHistory).order_by(DownloadHistory.created_at.desc()).limit(10)
    )
    recent = [{
        "id": h.id, "torrent_id": h.torrent_id, "title": h.title,
        "size": h.size, "status": h.status, "discount_type": h.discount_type,
        "has_hr": h.has_hr if hasattr(h, "has_hr") else False,
        "discount_end_time": str(h.discount_end_time) if hasattr(h, "discount_end_time") and h.discount_end_time else None,
        "created_at": str(h.created_at),
    } for h in recent_result.scalars().all()]

    return {
        "accounts": acc_count,
        "rules": {"total": rule_count, "enabled": enabled_rules},
        "downloaders": dl_count,
        "history": {
            "total": total_history,
            "downloading": downloading,
            "seeding": seeding,
        },
        "recent_downloads": recent,
    }


@router.get("/accounts/{account_id}/stats")
async def get_account_stats(account_id: int, db: AsyncSession = Depends(get_db)):
    """获取单个账号统计"""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    return {
        "id": account.id,
        "username": account.username,
        "uploaded": account.uploaded,
        "downloaded": account.downloaded,
        "ratio": account.ratio,
        "bonus": account.bonus,
        "user_class": account.user_class,
        "uploaded_gb": round(account.uploaded / (1024**3), 2) if account.uploaded else 0,
        "downloaded_gb": round(account.downloaded / (1024**3), 2) if account.downloaded else 0,
        "last_refresh": str(account.last_refresh) if account.last_refresh else None,
    }


@router.get("/downloader-stats")
async def get_downloader_stats(db: AsyncSession = Depends(get_db)):
    """获取所有下载器状态面板"""
    result = await db.execute(select(Downloader).order_by(Downloader.id))
    stats_list = []
    for dl_model in result.scalars().all():
        try:
            dl = create_downloader(
                dl_model.type, host=dl_model.host, port=dl_model.port,
                username=dl_model.username, password=dl_model.password, use_ssl=dl_model.use_ssl,
            )
            stats = await dl.get_stats()
            stats_list.append({
                "id": dl_model.id, "name": dl_model.name, "type": dl_model.type,
                "online": True,
                "download_speed": stats.download_speed,
                "upload_speed": stats.upload_speed,
                "downloading_count": stats.downloading_count,
                "seeding_count": stats.seeding_count,
                "free_space": stats.free_space,
                "free_space_gb": round(stats.free_space / (1024**3), 2) if stats.free_space else 0,
            })
        except Exception:
            stats_list.append({
                "id": dl_model.id, "name": dl_model.name,
                "type": dl_model.type, "online": False,
            })
    return stats_list


@router.get("/stats-trend")
async def get_stats_trend(hours: int = 24, db: AsyncSession = Depends(get_db)):
    """获取统计趋势数据（上传趋势 + 上传速率）"""
    from datetime import datetime, timedelta
    from models import StatsSnapshot

    since = datetime.utcnow() - timedelta(hours=hours)
    result = await db.execute(
        select(StatsSnapshot)
        .where(StatsSnapshot.created_at >= since)
        .order_by(StatsSnapshot.created_at.asc())
    )
    snapshots = result.scalars().all()

    # 按时间聚合（如果有多个账号，取总和）
    time_map: dict[str, dict] = {}
    for s in snapshots:
        # 按分钟取整
        t_key = s.created_at.strftime("%m-%d %H:%M") if s.created_at else "unknown"
        if t_key not in time_map:
            time_map[t_key] = {
                "time": t_key,
                "uploaded": 0,
                "downloaded": 0,
                "upload_speed": 0,
                "download_speed": 0,
            }
        time_map[t_key]["uploaded"] += s.uploaded or 0
        time_map[t_key]["downloaded"] += s.downloaded or 0
        # 速率取最大值（同一时间点多个账号共享同一速率）
        time_map[t_key]["upload_speed"] = max(time_map[t_key]["upload_speed"], s.upload_speed or 0)
        time_map[t_key]["download_speed"] = max(time_map[t_key]["download_speed"], s.download_speed or 0)

    points = list(time_map.values())

    # 转换为 GB 和 MB/s
    for p in points:
        p["uploaded_gb"] = round(p["uploaded"] / (1024**3), 2)
        p["downloaded_gb"] = round(p["downloaded"] / (1024**3), 2)
        p["upload_speed_mbps"] = round(p["upload_speed"] / (1024**2), 2)
        p["download_speed_mbps"] = round(p["download_speed"] / (1024**2), 2)

    return {"points": points, "count": len(points)}
