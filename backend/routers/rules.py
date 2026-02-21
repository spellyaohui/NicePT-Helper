"""自动下载规则路由"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import FilterRule
from utils.auth import get_current_user

router = APIRouter(prefix="/rules", tags=["规则"], dependencies=[Depends(get_current_user)])


class RuleCreate(BaseModel):
    name: str
    rule_type: str = "normal"
    free_only: bool = False
    double_upload: bool = False
    skip_hr: bool = False  # 跳过 H&R 种子
    min_size: Optional[float] = None
    max_size: Optional[float] = None
    min_seeders: Optional[int] = None
    max_seeders: Optional[int] = None
    min_leechers: Optional[int] = None
    max_leechers: Optional[int] = None
    keywords: str = ""
    exclude_keywords: str = ""
    categories: str = ""
    max_publish_hours: Optional[int] = None
    max_downloading: int = 5
    downloader_id: Optional[int] = None
    save_path: str = ""
    tags: str = ""
    account_id: Optional[int] = None
    sort_order: int = 0


class RuleResponse(BaseModel):
    id: int
    name: str
    enabled: bool
    rule_type: str
    free_only: bool
    double_upload: bool
    skip_hr: bool
    min_size: Optional[float]
    max_size: Optional[float]
    min_seeders: Optional[int]
    max_seeders: Optional[int]
    min_leechers: Optional[int]
    max_leechers: Optional[int]
    keywords: str
    exclude_keywords: str
    categories: str
    max_publish_hours: Optional[int]
    max_downloading: int
    downloader_id: Optional[int]
    save_path: str
    tags: str
    account_id: Optional[int]
    sort_order: int

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[RuleResponse])
async def list_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FilterRule).order_by(FilterRule.sort_order))
    return result.scalars().all()


@router.post("/", response_model=RuleResponse)
async def create_rule(req: RuleCreate, db: AsyncSession = Depends(get_db)):
    rule = FilterRule(**req.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FilterRule).where(FilterRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    return rule


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(rule_id: int, req: RuleCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FilterRule).where(FilterRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    for key, val in req.model_dump().items():
        setattr(rule, key, val)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}")
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FilterRule).where(FilterRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    await db.delete(rule)
    await db.commit()
    return {"message": "规则已删除"}


@router.post("/{rule_id}/toggle")
async def toggle_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FilterRule).where(FilterRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    rule.enabled = not rule.enabled
    await db.commit()
    return {"enabled": rule.enabled}
