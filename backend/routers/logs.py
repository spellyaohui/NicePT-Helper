"""日志管理路由"""
import os
import glob
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from utils.auth import get_current_user

router = APIRouter(prefix="/logs", tags=["日志"], dependencies=[Depends(get_current_user)])

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")


def _ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


@router.get("/")
async def list_logs(days: int = Query(None)):
    """获取日志文件列表，可选按天数过滤"""
    _ensure_log_dir()
    files = []
    for f in sorted(glob.glob(os.path.join(LOG_DIR, "*.log")), reverse=True):
        stat = os.stat(f)
        name = os.path.basename(f)
        mtime = datetime.fromtimestamp(stat.st_mtime)
        if days and mtime < datetime.now() - timedelta(days=days):
            continue
        files.append({
            "filename": name,
            "size": stat.st_size,
            "modified": mtime.isoformat(),
        })
    return files


@router.get("/{filename}")
async def read_log(filename: str, tail: int = Query(200, ge=1, le=5000)):
    """读取日志文件（默认最后 200 行）"""
    _ensure_log_dir()
    path = os.path.join(LOG_DIR, filename)
    if not os.path.isfile(path) or ".." in filename:
        raise HTTPException(status_code=404, detail="日志文件不存在")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    return {"filename": filename, "lines": lines[-tail:], "total_lines": len(lines)}


@router.delete("/{filename}")
async def delete_log(filename: str):
    """删除单个日志文件"""
    _ensure_log_dir()
    path = os.path.join(LOG_DIR, filename)
    if not os.path.isfile(path) or ".." in filename:
        raise HTTPException(status_code=404, detail="日志文件不存在")
    os.remove(path)
    return {"message": f"日志 {filename} 已删除"}


@router.delete("/")
async def clean_logs(days: int = Query(7)):
    """清理指定天数前的日志"""
    _ensure_log_dir()
    cutoff = datetime.now() - timedelta(days=days)
    removed = 0
    for f in glob.glob(os.path.join(LOG_DIR, "*.log")):
        if datetime.fromtimestamp(os.stat(f).st_mtime) < cutoff:
            os.remove(f)
            removed += 1
    return {"message": f"已清理 {removed} 个日志文件", "removed": removed}
