"""种子搜索与详情路由"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Account
from utils.auth import get_current_user
from services.site_adapter import NexusPHPAdapter, SearchParams

router = APIRouter(prefix="/torrents", tags=["种子"], dependencies=[Depends(get_current_user)])


class SearchRequest(BaseModel):
    account_id: int
    keyword: str = ""
    category: int = 0
    spstate: int = 0  # 0=全部, 2=免费, 3=2X, 4=2X免费
    incldead: int = 0  # 0=活种, 1=全部
    page: int = 0


class TorrentResponse(BaseModel):
    id: str
    title: str
    subtitle: str = ""
    category: str = ""
    size: float = 0
    seeders: int = 0
    leechers: int = 0
    completions: int = 0
    discount_type: str = ""
    discount_end_time: str = ""
    is_free: bool = False
    has_hr: bool = False
    download_status: str = ""  # seeding/downloading/completed/"" (空=未下载)
    download_progress: float = 0
    detail_url: str = ""
    download_url: str = ""


async def _get_adapter(account_id: int, db: AsyncSession) -> tuple[NexusPHPAdapter, Account]:
    """获取站点适配器"""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    return NexusPHPAdapter(account.site_url, account.cookie), account


@router.post("/search", response_model=list[TorrentResponse])
async def search_torrents(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    """搜索种子"""
    adapter, _ = await _get_adapter(req.account_id, db)
    try:
        params = SearchParams(
            keyword=req.keyword,
            category=req.category,
            spstate=req.spstate,
            incldead=req.incldead,
            page=req.page,
        )
        torrents = await adapter.search_torrents(params)
        return [TorrentResponse(
            id=t.id, title=t.title, subtitle=t.subtitle,
            category=t.category, size=t.size,
            seeders=t.seeders, leechers=t.leechers, completions=t.completions,
            discount_type=t.discount_type,
            discount_end_time=t.discount_end_time,
            is_free=t.is_free,
            has_hr=t.has_hr,
            download_status=t.download_status,
            download_progress=t.download_progress,
            detail_url=t.detail_url, download_url=t.download_url,
        ) for t in torrents]
    finally:
        await adapter.close()


# NicePT 分类映射（NexusPHP 标准分类）
NICEPT_CATEGORIES = {
    401: "电影/Movies",
    402: "电视剧/TV Series",
    403: "综艺/TV Shows",
    404: "纪录片/Documentaries",
    405: "动漫/Animations",
    406: "MV/Music Videos",
    407: "体育/Sports",
    408: "音乐/Music",
    409: "其他/Other",
    410: "游戏/Games",
    411: "软件/Software",
    412: "学习/Education",
}


@router.get("/categories")
async def get_categories():
    """获取种子分类列表"""
    return [{"id": k, "name": v} for k, v in NICEPT_CATEGORIES.items()]


@router.get("/metadata")
async def get_metadata():
    """获取种子搜索元数据（分类、促销类型等）"""
    return {
        "categories": [{"id": k, "name": v} for k, v in NICEPT_CATEGORIES.items()],
        "promotion_types": [
            {"id": 0, "name": "全部"},
            {"id": 2, "name": "免费"},
            {"id": 3, "name": "2X上传"},
            {"id": 4, "name": "2X免费"},
            {"id": 5, "name": "50%下载"},
            {"id": 6, "name": "2X/50%下载"},
        ],
        "incldead_options": [
            {"id": 0, "name": "活种"},
            {"id": 1, "name": "全部（含断种）"},
        ],
    }


@router.get("/{torrent_id}")
async def get_torrent_detail(
    torrent_id: str,
    account_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """获取种子详情"""
    adapter, _ = await _get_adapter(account_id, db)
    try:
        torrent = await adapter.get_torrent_detail(torrent_id)
        return TorrentResponse(
            id=torrent.id, title=torrent.title, subtitle=torrent.subtitle,
            category=torrent.category, size=torrent.size,
            seeders=torrent.seeders, leechers=torrent.leechers,
            discount_type=torrent.discount_type,
            discount_end_time=torrent.discount_end_time,
            is_free=torrent.is_free,
            has_hr=torrent.has_hr,
            download_status=torrent.download_status,
            download_progress=torrent.download_progress,
            detail_url=torrent.detail_url, download_url=torrent.download_url,
        )
    finally:
        await adapter.close()


@router.post("/{torrent_id}/download")
async def download_torrent(
    torrent_id: str,
    account_id: int = Query(...),
    downloader_id: Optional[int] = Query(None),
    save_path: str = Query(""),
    tags: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    """下载种子并推送到下载器"""
    from models import Downloader
    from services.downloader import create_downloader
    from models import DownloadHistory

    adapter, account = await _get_adapter(account_id, db)
    try:
        # 下载 .torrent 文件
        torrent_data = await adapter.download_torrent(torrent_id, account.passkey)

        # 获取种子信息
        torrent_info = await adapter.get_torrent_detail(torrent_id)

        # 推送到下载器
        if downloader_id:
            dl_result = await db.execute(select(Downloader).where(Downloader.id == downloader_id))
            dl = dl_result.scalar_one_or_none()
            if not dl:
                raise HTTPException(status_code=404, detail="下载器不存在")

            downloader = create_downloader(
                dl.type, host=dl.host, port=dl.port,
                username=dl.username, password=dl.password, use_ssl=dl.use_ssl,
            )
            info_hash = await downloader.add_torrent(torrent_data, save_path=save_path, tags=tags)

            # 记录下载历史（保存 H&R 和促销截止时间）
            _discount_end = None
            if torrent_info.discount_end_time:
                try:
                    _discount_end = datetime.strptime(torrent_info.discount_end_time, "%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    pass

            history = DownloadHistory(
                torrent_id=torrent_id,
                info_hash=info_hash,
                title=torrent_info.title,
                size=torrent_info.size,
                status="downloading",
                discount_type=torrent_info.discount_type,
                discount_end_time=_discount_end,
                has_hr=torrent_info.has_hr,
                account_id=account_id,
                downloader_id=downloader_id,
                tags=tags,
                save_path=save_path,
            )
            db.add(history)
            await db.commit()

            # 注册精确到期定时任务
            if _discount_end:
                await db.refresh(history)
                from services.scheduler import schedule_expiry_job
                schedule_expiry_job(history.id, torrent_id, _discount_end)

            return {"message": "种子已推送到下载器", "info_hash": info_hash}

        # 不指定下载器时返回种子文件
        from fastapi.responses import Response
        return Response(
            content=torrent_data,
            media_type="application/x-bittorrent",
            headers={"Content-Disposition": f"attachment; filename={torrent_id}.torrent"},
        )
    finally:
        await adapter.close()


@router.get("/{torrent_id}/download-url")
async def get_download_url(
    torrent_id: str,
    account_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """获取种子下载链接（含 passkey）"""
    _, account = await _get_adapter(account_id, db)
    url = f"{account.site_url}/download.php?id={torrent_id}"
    if account.passkey:
        url += f"&passkey={account.passkey}"
    return {"url": url}


class PushRequest(BaseModel):
    account_id: int
    torrent_id: str
    downloader_id: int
    save_path: str = ""
    tags: str = ""


@router.post("/push")
async def push_torrent(req: PushRequest, db: AsyncSession = Depends(get_db)):
    """批量推送种子到下载器（可用于规则手动触发）"""
    from models import Downloader, DownloadHistory
    from services.downloader import create_downloader

    adapter, account = await _get_adapter(req.account_id, db)
    try:
        dl_result = await db.execute(select(Downloader).where(Downloader.id == req.downloader_id))
        dl = dl_result.scalar_one_or_none()
        if not dl:
            raise HTTPException(status_code=404, detail="下载器不存在")

        downloader = create_downloader(
            dl.type, host=dl.host, port=dl.port,
            username=dl.username, password=dl.password, use_ssl=dl.use_ssl,
        )

        torrent_data = await adapter.download_torrent(req.torrent_id, account.passkey)
        torrent_info = await adapter.get_torrent_detail(req.torrent_id)
        info_hash = await downloader.add_torrent(torrent_data, save_path=req.save_path, tags=req.tags)

        # 解析促销截止时间
        _discount_end = None
        if torrent_info.discount_end_time:
            try:
                _discount_end = datetime.strptime(torrent_info.discount_end_time, "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                pass

        history = DownloadHistory(
            torrent_id=req.torrent_id,
            info_hash=info_hash,
            title=torrent_info.title,
            size=torrent_info.size,
            status="downloading",
            discount_type=torrent_info.discount_type,
            discount_end_time=_discount_end,
            has_hr=torrent_info.has_hr,
            account_id=req.account_id,
            downloader_id=req.downloader_id,
            tags=req.tags,
            save_path=req.save_path,
        )
        db.add(history)
        await db.commit()

        # 注册精确到期定时任务
        if _discount_end:
            await db.refresh(history)
            from services.scheduler import schedule_expiry_job
            schedule_expiry_job(history.id, req.torrent_id, _discount_end)

        return {"message": "种子已推送", "info_hash": info_hash, "title": torrent_info.title}
    finally:
        await adapter.close()
