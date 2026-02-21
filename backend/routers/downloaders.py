"""下载器管理路由"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Downloader
from utils.auth import get_current_user
from services.downloader import create_downloader

router = APIRouter(prefix="/downloaders", tags=["下载器"], dependencies=[Depends(get_current_user)])


class DownloaderCreate(BaseModel):
    name: str
    type: str  # qbittorrent / transmission
    host: str
    port: int
    username: str = ""
    password: str = ""
    use_ssl: bool = False
    is_default: bool = False


class DownloaderResponse(BaseModel):
    id: int
    name: str
    type: str
    host: str
    port: int
    username: str
    use_ssl: bool
    is_default: bool
    model_config = {"from_attributes": True}


async def _get_dl(downloader_id: int, db: AsyncSession) -> Downloader:
    result = await db.execute(select(Downloader).where(Downloader.id == downloader_id))
    dl = result.scalar_one_or_none()
    if not dl:
        raise HTTPException(status_code=404, detail="下载器不存在")
    return dl


def _make_adapter(dl: Downloader):
    return create_downloader(
        dl.type, host=dl.host, port=dl.port,
        username=dl.username, password=dl.password, use_ssl=dl.use_ssl,
    )


# ========== 无路径参数的路由放前面 ==========

@router.get("/", response_model=list[DownloaderResponse])
async def list_downloaders(db: AsyncSession = Depends(get_db)):
    """获取所有下载器"""
    result = await db.execute(select(Downloader).order_by(Downloader.id))
    return result.scalars().all()


@router.post("/", response_model=DownloaderResponse)
async def create_dl(req: DownloaderCreate, db: AsyncSession = Depends(get_db)):
    """添加下载器"""
    dl = Downloader(**req.model_dump())
    db.add(dl)
    await db.commit()
    await db.refresh(dl)
    return dl


@router.post("/test")
async def test_connection(req: DownloaderCreate):
    """测试下载器连接（未保存）"""
    dl = create_downloader(
        req.type, host=req.host, port=req.port,
        username=req.username, password=req.password, use_ssl=req.use_ssl,
    )
    ok = await dl.test_connection()
    return {"success": ok, "message": "连接成功" if ok else "连接失败"}


@router.get("/stats")
async def get_all_dl_stats(db: AsyncSession = Depends(get_db)):
    """获取所有下载器汇总统计"""
    result = await db.execute(select(Downloader).order_by(Downloader.id))
    stats_list = []
    for dl_model in result.scalars().all():
        try:
            adapter = _make_adapter(dl_model)
            stats = await adapter.get_stats()
            stats_list.append({
                "id": dl_model.id, "name": dl_model.name, "type": dl_model.type,
                "online": True,
                "download_speed": stats.download_speed,
                "upload_speed": stats.upload_speed,
                "downloading_count": stats.downloading_count,
                "seeding_count": stats.seeding_count,
                "free_space": stats.free_space,
            })
        except Exception:
            stats_list.append({
                "id": dl_model.id, "name": dl_model.name,
                "type": dl_model.type, "online": False,
            })
    return stats_list


# ========== 带路径参数的路由 ==========

@router.post("/{downloader_id}/test")
async def test_existing(downloader_id: int, db: AsyncSession = Depends(get_db)):
    """测试已保存的下载器连接"""
    dl = await _get_dl(downloader_id, db)
    ok = await _make_adapter(dl).test_connection()
    return {"success": ok, "message": "连接成功" if ok else "连接失败"}


@router.delete("/{downloader_id}")
async def delete_dl(downloader_id: int, db: AsyncSession = Depends(get_db)):
    """删除下载器"""
    dl = await _get_dl(downloader_id, db)
    await db.delete(dl)
    await db.commit()
    return {"message": "下载器已删除"}


@router.get("/{downloader_id}/stats")
async def get_dl_stats(downloader_id: int, db: AsyncSession = Depends(get_db)):
    """获取单个下载器统计"""
    dl = await _get_dl(downloader_id, db)
    stats = await _make_adapter(dl).get_stats()
    return {
        "download_speed": stats.download_speed,
        "upload_speed": stats.upload_speed,
        "downloading_count": stats.downloading_count,
        "seeding_count": stats.seeding_count,
        "free_space": stats.free_space,
    }


@router.get("/{downloader_id}/tags")
async def get_dl_tags(downloader_id: int, db: AsyncSession = Depends(get_db)):
    """获取下载器标签"""
    dl = await _get_dl(downloader_id, db)
    tags = await _make_adapter(dl).get_tags()
    return {"tags": tags}


@router.get("/{downloader_id}/disk-space")
async def get_dl_disk_space(downloader_id: int, db: AsyncSession = Depends(get_db)):
    """获取下载器磁盘空间"""
    dl = await _get_dl(downloader_id, db)
    stats = await _make_adapter(dl).get_stats()
    return {
        "free_space": stats.free_space,
        "total_space": stats.total_space,
        "free_space_gb": round(stats.free_space / (1024**3), 2) if stats.free_space else 0,
    }
