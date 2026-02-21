"""
NicePT 站点登录服务

NicePT 使用 Challenge-Response 认证机制：
1. 请求 login.php 获取验证码图片 + imagehash + session cookie
2. 调用 /api/challenge 获取 challenge 和 secret
3. 计算 response:
   - clientHash = sha256(password)
   - serverHash = sha256(secret + clientHash)
   - response = hmac_sha256(challenge, serverHash)
4. 提交表单到 takelogin.php（带 response、imagestring、imagehash）
"""
import re
import hashlib
import hmac
import logging
import base64
import uuid
from dataclasses import dataclass, field
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class LoginSession:
    """登录会话"""
    session_id: str
    site_url: str
    cookies: dict
    captcha_image: str  # base64 data URI
    imagehash: str  # 验证码对应的 hash
    hidden_fields: dict


# 内存中保存登录会话
_login_sessions: dict[str, LoginSession] = {}


def get_login_session(session_id: str) -> Optional[LoginSession]:
    return _login_sessions.get(session_id)


def remove_login_session(session_id: str):
    _login_sessions.pop(session_id, None)


def _sha256(text: str) -> str:
    """SHA256 哈希"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hmac_sha256(key: str, message: str) -> str:
    """HMAC-SHA256"""
    return hmac.new(key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


async def init_login(site_url: str) -> LoginSession:
    """
    第一步：获取登录页面和验证码

    返回验证码图片（base64）、imagehash、session cookie
    """
    site_url = site_url.rstrip("/")

    async with httpx.AsyncClient(
        timeout=settings.request_timeout,
        headers={"User-Agent": settings.user_agent},
        follow_redirects=True,
        verify=False,
    ) as client:
        # 1. 请求登录页面
        login_resp = await client.get(f"{site_url}/login.php")
        login_resp.raise_for_status()
        cookies = dict(login_resp.cookies)

        soup = BeautifulSoup(login_resp.text, "lxml")

        # 2. 提取隐藏字段
        hidden_fields = {}
        form = soup.find("form", {"action": "takelogin.php"})
        if form:
            for inp in form.find_all("input", {"type": "hidden"}):
                name = inp.get("name")
                value = inp.get("value", "")
                if name:
                    hidden_fields[name] = value

        imagehash = hidden_fields.get("imagehash", "")

        # 3. 获取验证码图片
        captcha_b64 = ""
        captcha_img = soup.find("img", alt="CAPTCHA")
        if not captcha_img:
            # 备选：查找 image.php 的 img
            captcha_img = soup.find("img", src=re.compile(r"image\.php"))

        if captcha_img:
            captcha_src = captcha_img.get("src", "")
            if captcha_src and not captcha_src.startswith("http"):
                captcha_src = f"{site_url}/{captcha_src.lstrip('/')}"

            if captcha_src:
                captcha_resp = await client.get(captcha_src, cookies=cookies)
                captcha_resp.raise_for_status()
                b64_data = base64.b64encode(captcha_resp.content).decode()
                content_type = captcha_resp.headers.get("content-type", "image/png")
                captcha_b64 = f"data:{content_type};base64,{b64_data}"
                cookies.update(dict(captcha_resp.cookies))
                logger.info("验证码图片获取成功")

        # 4. 创建会话
        session_id = str(uuid.uuid4())
        session = LoginSession(
            session_id=session_id,
            site_url=site_url,
            cookies=cookies,
            captcha_image=captcha_b64,
            imagehash=imagehash,
            hidden_fields=hidden_fields,
        )
        _login_sessions[session_id] = session
        return session


async def submit_login(
    session_id: str,
    username: str,
    password: str,
    captcha: str,
    two_step_code: str = "",
) -> dict:
    """
    第二步：执行 Challenge-Response 登录

    流程：
    1. 调用 /api/challenge 获取 challenge + secret
    2. 计算 response
    3. 提交 takelogin.php
    """
    session = get_login_session(session_id)
    if not session:
        return {"success": False, "cookie": "", "uid": "", "message": "登录会话已过期，请重新获取验证码"}

    site_url = session.site_url

    async with httpx.AsyncClient(
        timeout=settings.request_timeout,
        headers={"User-Agent": settings.user_agent},
        follow_redirects=False,
        verify=False,
    ) as client:
        # 1. 获取 challenge
        challenge_resp = await client.post(
            f"{site_url}/api/challenge",
            json={"username": username},
            cookies=session.cookies,
            headers={
                "User-Agent": settings.user_agent,
                "Content-Type": "application/json",
                "Referer": f"{site_url}/login.php",
            },
        )
        challenge_data = challenge_resp.json()
        logger.info(f"Challenge 响应: ret={challenge_data.get('ret')}")

        if challenge_data.get("ret") != 0:
            msg = challenge_data.get("msg", "获取 challenge 失败")
            remove_login_session(session_id)
            return {"success": False, "cookie": "", "uid": "", "message": msg}

        challenge = challenge_data["data"]["challenge"]
        secret = challenge_data["data"]["secret"]

        # 合并 challenge 请求的 cookie
        cookies = {**session.cookies, **dict(challenge_resp.cookies)}

        # 2. 计算 response
        client_hashed = _sha256(password)
        server_hash = _sha256(secret + client_hashed)
        response = _hmac_sha256(challenge, server_hash)

        # 3. 构建表单数据
        form_data = {
            "username": username,
            "imagestring": captcha,
            "imagehash": session.imagehash,
            "secret": session.hidden_fields.get("secret", ""),
            "response": response,
        }
        if two_step_code:
            form_data["two_step_code"] = two_step_code

        # 4. 提交登录
        login_resp = await client.post(
            f"{site_url}/takelogin.php",
            data=form_data,
            cookies=cookies,
            headers={
                "User-Agent": settings.user_agent,
                "Referer": f"{site_url}/login.php",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

        all_cookies = {**cookies, **dict(login_resp.cookies)}

        # 5. 判断登录结果
        if login_resp.status_code in (301, 302):
            location = login_resp.headers.get("location", "")
            if "index" in location or "my" in location or location == "/" or not location:
                cookie_str = "; ".join(f"{k}={v}" for k, v in all_cookies.items())
                uid = _extract_uid_from_cookies(all_cookies)

                if not uid:
                    uid = await _extract_uid_from_index(client, site_url, all_cookies)

                remove_login_session(session_id)
                logger.info(f"登录成功: {username}, UID: {uid}")
                return {
                    "success": True,
                    "cookie": cookie_str,
                    "uid": uid,
                    "message": "登录成功",
                }

        # 登录失败
        error_msg = _parse_error(login_resp)
        remove_login_session(session_id)
        logger.warning(f"登录失败: {error_msg}")
        return {"success": False, "cookie": "", "uid": "", "message": error_msg}


def _parse_error(resp: httpx.Response) -> str:
    """解析登录失败的错误信息"""
    if resp.status_code != 200:
        return f"登录失败 (HTTP {resp.status_code})"

    soup = BeautifulSoup(resp.text, "lxml")

    # NexusPHP 错误页面
    error_td = soup.find("td", class_="text")
    if error_td:
        return error_td.get_text(strip=True)

    # 尝试从 h2 提取
    h2 = soup.find("h2")
    if h2:
        return h2.get_text(strip=True)

    body_text = soup.get_text(strip=True)
    if "验证码" in body_text or "驗證碼" in body_text:
        return "验证码错误"
    if "密码" in body_text or "密碼" in body_text:
        return "用户名或密码错误"

    return "登录失败，请检查用户名、密码和验证码"


def _extract_uid_from_cookies(cookies: dict) -> str:
    """从 cookie 中提取用户 ID"""
    for key in ["c_secure_uid", "uid", "userid"]:
        if key in cookies:
            val = cookies[key]
            if key == "c_secure_uid":
                try:
                    decoded = base64.b64decode(val).decode()
                    match = re.search(r"\d+", decoded)
                    if match:
                        return match.group()
                except Exception:
                    pass
            match = re.search(r"\d+", str(val))
            if match:
                return match.group()
    return ""


async def _extract_uid_from_index(
    client: httpx.AsyncClient, site_url: str, cookies: dict
) -> str:
    """从首页提取用户 ID"""
    try:
        resp = await client.get(
            f"{site_url}/index.php",
            cookies=cookies,
            follow_redirects=True,
            headers={"User-Agent": settings.user_agent},
        )
        soup = BeautifulSoup(resp.text, "lxml")
        link = soup.find("a", href=re.compile(r"userdetails\.php\?id=\d+"))
        if link:
            match = re.search(r"id=(\d+)", link.get("href", ""))
            if match:
                return match.group(1)
    except Exception as e:
        logger.debug(f"从首页提取 UID 失败: {e}")
    return ""
