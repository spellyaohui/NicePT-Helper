"""下载历史路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import DownloadHistory, Downloader
from utils.auth import get_current_user
from services.downloader import create_downloader

router = APIRouter(prefix="/history", tags=["下载历史"], dependencies=[Depends(get_current_user)])


@router.get("/")
async def list_history(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取下载历史（分页）"""
    query = select(DownloadHistory).order_by(DownloadHistory.created_at.desc())
    if status:
        query = query.where(DownloadHistory.status == status)

    # 总数
    count_query = select(func.count()).select_from(DownloadHistory)
    if status:
        count_query = count_query.where(DownloadHistory.status == status)
    total = (await db.execute(count_query)).scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    items = result.scalars().all()

    return {
        "items": [
            {
                "id": h.id, "torrent_id": h.torrent_id, "info_hash": h.info_hash,
                "title": h.title, "size": h.size, "status": h.status,
                "discount_type": h.discount_type, "tags": h.tags,
                "account_id": h.account_id, "downloader_id": h.downloader_id,
                "rule_id": h.rule_id,
                "created_at": str(h.created_at),
                "updated_at": str(h.updated_at),
            }
            for h in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/status-mapping")
async def status_mapping():
    """获取状态映射说明"""
    return {
        "downloading": "下载中",
        "seeding": "做种中",
        "completed": "已完成",
        "paused": "已暂停",
        "deleted": "已删除",
        "expired_deleted": "促销过期删除",
        "dynamic_deleted": "动态容量删除",
        "unregistered_deleted": "站点下架删除",
    }


@router.post("/sync-status")
async def sync_status(db: AsyncSession = Depends(get_db)):
    """手动触发状态同步"""
    from services.scheduler import sync_download_status
    await sync_download_status()
    return {"message": "状态同步完成"}


@router.get("/check-expired")
async def check_expired(db: AsyncSession = Depends(get_db)):
    """手动触发过期检查"""
    from services.scheduler import check_expired_torrents
    await check_expired_torrents()
    return {"message": "过期检查完成"}


@router.post("/import-from-downloader")
async def import_from_downloader(
    downloader_id: int = Query(...),
    account_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """从下载器导入种子到历史记录"""
    dl_result = await db.execute(select(Downloader).where(Downloader.id == downloader_id))
    dl_model = dl_result.scalar_one_or_none()
    if not dl_model:
        raise HTTPException(status_code=404, detail="下载器不存在")

    downloader = create_downloader(
        dl_model.type, host=dl_model.host, port=dl_model.port,
        username=dl_model.username, password=dl_model.password, use_ssl=dl_model.use_ssl,
    )

    all_torrents = await downloader.get_all_torrents()

    # 获取已有的 info_hash
    existing = await db.execute(select(DownloadHistory.info_hash))
    existing_hashes = {row[0].lower() for row in existing.all() if row[0]}

    imported = 0
    for t in all_torrents:
        if t.info_hash.lower() in existing_hashes:
            continue
        history = DownloadHistory(
            torrent_id="",  # 从下载器导入时不知道站点 ID
            info_hash=t.info_hash,
            title=t.name,
            size=t.total_size,
            status=t.state,
            account_id=account_id,
            downloader_id=downloader_id,
            tags=",".join(t.tags) if hasattr(t, "tags") and t.tags else "",
        )
        db.add(history)
        imported += 1

    await db.commit()
    return {"message": f"已导入 {imported} 个种子", "imported": imported}


class UploadTorrentRequest(BaseModel):
    account_id: int
    torrent_id: str
    downloader_id: int
    save_path: str = ""
    tags: str = ""


@router.post("/upload-torrent")
async def upload_torrent(req: UploadTorrentRequest, db: AsyncSession = Depends(get_db)):
    """手动上传种子到下载器"""
    from models import Account
    from services.site_adapter import NexusPHPAdapter

    # 获取账号
    acc_result = await db.execute(select(Account).where(Account.id == req.account_id))
    account = acc_result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    # 获取下载器
    dl_result = await db.execute(select(Downloader).where(Downloader.id == req.downloader_id))
    dl_model = dl_result.scalar_one_or_none()
    if not dl_model:
        raise HTTPException(status_code=404, detail="下载器不存在")

    # 下载 .torrent
    adapter = NexusPHPAdapter(account.site_url, account.cookie)
    try:
        torrent_data = await adapter.download_torrent(req.torrent_id, account.passkey)
        torrent_info = await adapter.get_torrent_detail(req.torrent_id)
    finally:
        await adapter.close()

    # 推送到下载器
    downloader = create_downloader(
        dl_model.type, host=dl_model.host, port=dl_model.port,
        username=dl_model.username, password=dl_model.password, use_ssl=dl_model.use_ssl,
    )
    info_hash = await downloader.add_torrent(torrent_data, save_path=req.save_path, tags=req.tags)

    # 记录历史
    history = DownloadHistory(
        torrent_id=req.torrent_id,
        info_hash=info_hash,
        title=torrent_info.title,
        size=torrent_info.size,
        status="downloading",
        discount_type=torrent_info.discount_type,
        account_id=req.account_id,
        downloader_id=req.downloader_id,
        tags=req.tags,
        save_path=req.save_path,
    )
    db.add(history)
    await db.commit()

    return {"message": "种子已推送到下载器", "info_hash": info_hash}


@router.delete("/deleted")
async def clear_deleted(db: AsyncSession = Depends(get_db)):
    """快捷清除所有已删除状态的历史记录"""
    result = await db.execute(
        delete(DownloadHistory).where(
            DownloadHistory.status.in_(["deleted", "expired_deleted", "dynamic_deleted", "unregistered_deleted"])
        )
    )
    await db.commit()
    return {"message": f"已清除 {result.rowcount} 条已删除记录"}


@router.delete("/{history_id}")
async def delete_history(
    history_id: int,
    delete_from_downloader: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """删除历史记录"""
    result = await db.execute(select(DownloadHistory).where(DownloadHistory.id == history_id))
    history = result.scalar_one_or_none()
    if not history:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 联动删除下载器中的种子
    if delete_from_downloader and history.info_hash and history.downloader_id:
        try:
            dl_result = await db.execute(
                select(Downloader).where(Downloader.id == history.downloader_id)
            )
            dl_model = dl_result.scalar_one_or_none()
            if dl_model:
                dl = create_downloader(
                    dl_model.type, host=dl_model.host, port=dl_model.port,
                    username=dl_model.username, password=dl_model.password, use_ssl=dl_model.use_ssl,
                )
                await dl.remove_torrent(history.info_hash, delete_files=True)
        except Exception:
            pass  # 下载器删除失败不阻塞历史删除

    await db.delete(history)
    await db.commit()
    return {"message": "记录已删除"}


@router.delete("/")
async def clear_history(
    status: str = Query(..., description="要清除的状态，如 deleted"),
    db: AsyncSession = Depends(get_db),
):
    """批量清除指定状态的历史记录"""
    result = await db.execute(
        delete(DownloadHistory).where(DownloadHistory.status == status)
    )
    await db.commit()
    return {"message": f"已清除 {result.rowcount} 条 {status} 状态的记录"}


@router.get("/downloader-tags/{downloader_id}")
async def get_downloader_tags(downloader_id: int, db: AsyncSession = Depends(get_db)):
    """获取下载器标签列表"""
    dl_result = await db.execute(select(Downloader).where(Downloader.id == downloader_id))
    dl_model = dl_result.scalar_one_or_none()
    if not dl_model:
        raise HTTPException(status_code=404, detail="下载器不存在")

    dl = create_downloader(
        dl_model.type, host=dl_model.host, port=dl_model.port,
        username=dl_model.username, password=dl_model.password, use_ssl=dl_model.use_ssl,
    )
    tags = await dl.get_tags()
    return {"tags": tags}
