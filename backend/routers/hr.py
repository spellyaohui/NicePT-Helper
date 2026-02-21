"""H&R 考核路由"""
import logging
from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import HitAndRun, Account
from utils.auth import get_current_user
from services.site_adapter import NexusPHPAdapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hr", tags=["H&R 考核"], dependencies=[Depends(get_current_user)])

# 状态映射
STATUS_MAP = {
    "inspecting": "考核中",
    "reached": "已达标",
    "unreached": "未达标",
    "pardoned": "已豁免",
}

STATUS_PARAM = {
    "inspecting": 1,
    "reached": 2,
    "unreached": 3,
    "pardoned": 4,
}


@router.get("/")
async def list_hr(
    status: Optional[str] = Query("inspecting"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取 H&R 考核列表（从本地数据库）"""
    query = select(HitAndRun).order_by(HitAndRun.hr_id.desc())
    count_query = select(func.count()).select_from(HitAndRun)

    if status:
        query = query.where(HitAndRun.status == status)
        count_query = count_query.where(HitAndRun.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    items = result.scalars().all()

    return {
        "items": [
            {
                "id": h.id, "hr_id": h.hr_id,
                "torrent_id": h.torrent_id, "torrent_name": h.torrent_name,
                "uploaded": h.uploaded, "downloaded": h.downloaded,
                "share_ratio": h.share_ratio,
                "seed_time_required": h.seed_time_required,
                "completed_at": h.completed_at,
                "inspect_time_left": h.inspect_time_left,
                "comment": h.comment, "status": h.status,
                "account_id": h.account_id,
                "updated_at": str(h.updated_at),
            }
            for h in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/summary")
async def hr_summary(db: AsyncSession = Depends(get_db)):
    """H&R 各状态统计"""
    result = {}
    for status_key in STATUS_MAP:
        count = (await db.execute(
            select(func.count()).select_from(HitAndRun).where(HitAndRun.status == status_key)
        )).scalar() or 0
        result[status_key] = count
    return result


@router.post("/sync")
async def sync_hr(
    account_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """从站点同步 H&R 考核数据"""
    acc_result = await db.execute(select(Account).where(Account.id == account_id))
    account = acc_result.scalar_one_or_none()
    if not account:
        return {"error": "账号不存在"}

    adapter = NexusPHPAdapter(account.site_url, account.cookie)
    total_synced = 0

    try:
        # 遍历所有状态
        for status_key, status_param in STATUS_PARAM.items():
            records = await adapter.get_hr_list(status=status_param)
            for r in records:
                # 按 hr_id 更新或插入
                existing = await db.execute(
                    select(HitAndRun).where(HitAndRun.hr_id == r.hr_id)
                )
                hr = existing.scalar_one_or_none()
                if hr:
                    # 更新
                    hr.torrent_name = r.torrent_name or hr.torrent_name
                    hr.torrent_id = r.torrent_id or hr.torrent_id
                    hr.uploaded = r.uploaded
                    hr.downloaded = r.downloaded
                    hr.share_ratio = r.share_ratio
                    hr.seed_time_required = r.seed_time_required
                    hr.completed_at = r.completed_at
                    hr.inspect_time_left = r.inspect_time_left
                    hr.comment = r.comment
                    hr.status = status_key
                else:
                    # 新增
                    hr = HitAndRun(
                        hr_id=r.hr_id,
                        torrent_id=r.torrent_id,
                        torrent_name=r.torrent_name,
                        uploaded=r.uploaded,
                        downloaded=r.downloaded,
                        share_ratio=r.share_ratio,
                        seed_time_required=r.seed_time_required,
                        completed_at=r.completed_at,
                        inspect_time_left=r.inspect_time_left,
                        comment=r.comment,
                        status=status_key,
                        account_id=account_id,
                    )
                    db.add(hr)
                total_synced += 1

        await db.commit()
    finally:
        await adapter.close()

    logger.info(f"H&R 同步完成，共 {total_synced} 条记录")
    return {"message": f"同步完成，共 {total_synced} 条记录", "synced": total_synced}


@router.get("/status-mapping")
async def status_mapping():
    """获取状态映射"""
    return STATUS_MAP


@router.post("/remove/{hr_id}")
async def remove_hr(
    hr_id: int,
    account_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """消除 H&R（花费魔力值，通过站点 ajax.php 调用）"""
    acc_result = await db.execute(select(Account).where(Account.id == account_id))
    account = acc_result.scalar_one_or_none()
    if not account:
        return {"error": "账号不存在"}

    adapter = NexusPHPAdapter(account.site_url, account.cookie)
    try:
        result = await adapter.remove_hit_and_run(hr_id)
        if result.get("success"):
            # 更新本地记录状态
            existing = await db.execute(
                select(HitAndRun).where(HitAndRun.hr_id == hr_id)
            )
            hr = existing.scalar_one_or_none()
            if hr:
                hr.status = "pardoned"
                await db.commit()
        return result
    finally:
        await adapter.close()
