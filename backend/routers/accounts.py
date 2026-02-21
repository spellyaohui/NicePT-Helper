"""PT 账号管理路由"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Account
from utils.auth import get_current_user
from services.site_adapter import NexusPHPAdapter

router = APIRouter(prefix="/accounts", tags=["账号管理"], dependencies=[Depends(get_current_user)])


class AccountCreate(BaseModel):
    site_url: str
    username: str
    cookie: str
    uid: Optional[str] = ""


class AccountResponse(BaseModel):
    id: int
    site_name: str
    site_url: str
    username: str
    uid: str
    uploaded: float
    downloaded: float
    ratio: float
    bonus: float
    user_class: str
    is_active: bool

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[AccountResponse])
async def list_accounts(db: AsyncSession = Depends(get_db)):
    """获取所有账号"""
    result = await db.execute(select(Account).order_by(Account.id))
    return result.scalars().all()


@router.post("/", response_model=AccountResponse)
async def create_account(req: AccountCreate, db: AsyncSession = Depends(get_db)):
    """添加 PT 账号"""
    account = Account(
        site_url=req.site_url,
        username=req.username,
        cookie=req.cookie,
        uid=req.uid or "",
    )

    # 尝试获取 passkey
    try:
        adapter = NexusPHPAdapter(req.site_url, req.cookie)
        passkey = await adapter.get_passkey()
        account.passkey = passkey
        await adapter.close()
    except Exception:
        pass  # passkey 获取失败不阻塞创建

    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: int, db: AsyncSession = Depends(get_db)):
    """获取单个账号"""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    return account


@router.post("/{account_id}/refresh", response_model=AccountResponse)
async def refresh_account(account_id: int, db: AsyncSession = Depends(get_db)):
    """刷新账号数据"""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    adapter = NexusPHPAdapter(account.site_url, account.cookie)
    try:
        if not account.uid:
            raise HTTPException(status_code=400, detail="账号缺少 UID，请先设置")

        stats = await adapter.get_user_stats(account.uid)
        account.uploaded = stats.uploaded
        account.downloaded = stats.downloaded
        account.ratio = stats.ratio
        account.bonus = stats.bonus
        account.user_class = stats.user_class

        if stats.passkey:
            account.passkey = stats.passkey

        from datetime import datetime
        account.last_refresh = datetime.utcnow()
        await db.commit()
        await db.refresh(account)
    finally:
        await adapter.close()

    return account


@router.delete("/{account_id}")
async def delete_account(account_id: int, db: AsyncSession = Depends(get_db)):
    """删除账号"""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    await db.delete(account)
    await db.commit()
    return {"message": "账号已删除"}
