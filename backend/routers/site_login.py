"""
PT 站点登录路由

两步登录流程：
1. POST /site-login/init    → 获取验证码图片
2. POST /site-login/submit  → 提交用户名+密码+验证码，完成登录
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Account
from utils.auth import get_current_user
from services.login_service import init_login, submit_login
from services.site_adapter import NexusPHPAdapter

router = APIRouter(prefix="/site-login", tags=["站点登录"], dependencies=[Depends(get_current_user)])


class InitLoginRequest(BaseModel):
    site_url: str


class InitLoginResponse(BaseModel):
    session_id: str
    captcha_image: str  # base64 data URI
    has_captcha: bool


class SubmitLoginRequest(BaseModel):
    session_id: str
    site_url: str
    username: str
    password: str
    captcha: str = ""
    two_step_code: str = ""  # 两步验证码（如有设置）
    auto_save: bool = True  # 登录成功后自动保存为账号


class SubmitLoginResponse(BaseModel):
    success: bool
    message: str
    cookie: str = ""
    uid: str = ""
    account_id: Optional[int] = None


@router.post("/init", response_model=InitLoginResponse)
async def login_init(req: InitLoginRequest):
    """
    第一步：初始化登录，获取验证码

    返回验证码图片（base64）和 session_id，
    前端展示验证码图片让用户输入。
    """
    try:
        session = await init_login(req.site_url)
        return InitLoginResponse(
            session_id=session.session_id,
            captcha_image=session.captcha_image,
            has_captcha=bool(session.captcha_image),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"获取验证码失败: {str(e)}")


@router.post("/submit", response_model=SubmitLoginResponse)
async def login_submit(req: SubmitLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    第二步：提交登录

    提交用户名、密码、验证码，完成登录。
    登录成功后可自动保存为 PT 账号。
    """
    result = await submit_login(
        session_id=req.session_id,
        username=req.username,
        password=req.password,
        captcha=req.captcha,
        two_step_code=req.two_step_code,
    )

    if not result["success"]:
        return SubmitLoginResponse(
            success=False,
            message=result["message"],
        )

    account_id = None

    # 登录成功，自动保存账号
    if req.auto_save:
        account = Account(
            site_url=req.site_url,
            username=req.username,
            cookie=result["cookie"],
            uid=result["uid"],
        )

        # 尝试获取 passkey
        try:
            adapter = NexusPHPAdapter(req.site_url, result["cookie"])
            passkey = await adapter.get_passkey()
            account.passkey = passkey
            await adapter.close()
        except Exception:
            pass

        db.add(account)
        await db.commit()
        await db.refresh(account)
        account_id = account.id

    return SubmitLoginResponse(
        success=True,
        message="登录成功",
        cookie=result["cookie"],
        uid=result["uid"],
        account_id=account_id,
    )


@router.post("/refresh-captcha", response_model=InitLoginResponse)
async def refresh_captcha(req: InitLoginRequest):
    """刷新验证码（重新初始化登录会话）"""
    try:
        session = await init_login(req.site_url)
        return InitLoginResponse(
            session_id=session.session_id,
            captcha_image=session.captcha_image,
            has_captcha=bool(session.captcha_image),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"刷新验证码失败: {str(e)}")
