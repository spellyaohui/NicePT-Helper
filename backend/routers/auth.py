"""认证路由"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from utils.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["认证"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.get("/check-init")
async def check_init(db: AsyncSession = Depends(get_db)):
    """检查是否已初始化（是否有管理员）"""
    result = await db.execute(select(func.count(User.id)))
    count = result.scalar()
    return {"initialized": count > 0}


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """首次注册管理员"""
    # 检查是否已有用户
    result = await db.execute(select(func.count(User.id)))
    if result.scalar() > 0:
        raise HTTPException(status_code=400, detail="系统已初始化，不允许再次注册")

    user = User(username=req.username, hashed_password=hash_password(req.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id), "username": user.username})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """登录"""
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token({"sub": str(user.id), "username": user.username})
    return TokenResponse(access_token=token)


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """登出（前端清除 Token 即可，后端仅做确认）"""
    return {"message": "已登出"}


@router.get("/verify")
async def verify(current_user: dict = Depends(get_current_user)):
    """验证 Token"""
    return {"valid": True, "user": current_user}

