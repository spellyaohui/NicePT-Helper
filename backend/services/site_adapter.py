"""
NicePT 站点适配器（基于 NexusPHP）

通过 HTML 页面解析实现所有站点交互。
已根据 NicePT 实际页面结构调整解析器。
"""
import re
import asyncio
import logging
import time
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup, Tag

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class TorrentInfo:
    """种子信息"""
    id: str = ""
    title: str = ""
    subtitle: str = ""
    category: str = ""
    size: float = 0
    seeders: int = 0
    leechers: int = 0
    completions: int = 0
    upload_time: Optional[datetime] = None
    discount_type: str = ""
    discount_end_time: str = ""  # 促销截止时间，如 "2026-02-22 17:34:02"
    is_free: bool = False  # 是否免费（含 2x免费）
    uploader: str = ""
    detail_url: str = ""
    download_url: str = ""
    has_hr: bool = False  # H&R 标记（重要：影响账号安全）
    thumbnail: str = ""
    # 下载状态（从站点页面解析，需要登录态 Cookie）
    download_status: str = ""  # "seeding"/"downloading"/"completed"/"" (空=未下载)
    download_progress: float = 0  # 下载进度百分比，0-100


@dataclass
class UserStats:
    """用户统计信息"""
    uid: str = ""
    username: str = ""
    uploaded: float = 0
    downloaded: float = 0
    ratio: float = 0
    bonus: float = 0
    user_class: str = ""
    passkey: str = ""


@dataclass
class SearchParams:
    """搜索参数"""
    keyword: str = ""
    category: int = 0
    spstate: int = 0  # 0=全部, 2=免费, 3=2X, 4=2X免费, 5=50%, 6=2X50%, 7=30%
    incldead: int = 0  # 0=活种, 1=全部, 2=断种
    page: int = 0


@dataclass
class HRRecord:
    """H&R 考核记录"""
    hr_id: int = 0
    torrent_id: str = ""
    torrent_name: str = ""
    uploaded: float = 0       # 字节
    downloaded: float = 0     # 字节
    share_ratio: float = 0
    seed_time_required: str = ""  # 还需做种时间文本
    completed_at: str = ""        # 下载完成时间
    inspect_time_left: str = ""   # 剩余考核时间
    comment: str = ""
    status: str = "inspecting"    # inspecting / reached / unreached / pardoned


class NexusPHPAdapter:
    """NicePT 站点适配器"""

    def __init__(self, site_url: str, cookie: str):
        self.site_url = site_url.rstrip("/")
        self.cookie = cookie
        self._client: Optional[httpx.AsyncClient] = None
        self._last_request_time: float = 0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=settings.request_timeout,
                headers={
                    "User-Agent": settings.user_agent,
                    "Cookie": self.cookie,
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                },
                follow_redirects=True,
                verify=False,
            )
        return self._client

    async def _rate_limit(self):
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < settings.request_delay:
            await asyncio.sleep(settings.request_delay - elapsed)
        self._last_request_time = time.time()

    async def _get_page(self, path: str, params: dict = None) -> BeautifulSoup:
        await self._rate_limit()
        client = await self._get_client()
        url = f"{self.site_url}/{path}"
        logger.info(f"请求页面: {url}")
        response = await client.get(url, params=params)
        response.raise_for_status()
        if "login.php" in str(response.url) and "takelogin" not in str(response.url):
            raise Exception("Cookie 已失效，请重新登录")
        return BeautifulSoup(response.text, "lxml")

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ---- 用户相关 ----

    async def get_user_stats(self, uid: str) -> UserStats:
        """获取用户统计信息"""
        soup = await self._get_page("userdetails.php", {"id": uid})
        stats = UserStats(uid=uid)

        for td in soup.find_all("td", class_="rowhead"):
            label = td.get_text(strip=True)
            next_td = td.find_next_sibling("td")
            if not next_td:
                continue
            val = next_td.get_text(strip=True)

            if "用戶名" in label or "用户名" in label:
                stats.username = val
            elif "等級" in label or "等级" in label:
                img = next_td.find("img")
                stats.user_class = (img.get("title", "") or img.get("alt", "") or val) if img else val
            elif "魔力值" in label or "魔力" in label:
                stats.bonus = self._parse_number(val)
            elif "分享率" in label:
                stats.ratio = self._parse_ratio(val)
            elif "傳送" in label or "传送" in label:
                # 格式: "上傳量: 54.57 GB下載量: 0.00 KB實際上傳量: ..."
                stats.uploaded, stats.downloaded = self._parse_transfer_text(val)

        if stats.ratio == 0 and stats.downloaded > 0:
            stats.ratio = round(stats.uploaded / stats.downloaded, 3)

        return stats

    async def get_passkey(self) -> str:
        """从 usercp.php 获取 passkey"""
        soup = await self._get_page("usercp.php")
        for td in soup.find_all("td", class_="rowhead"):
            text = td.get_text(strip=True).lower()
            if "passkey" in text or "密鑰" in text or "密钥" in text:
                next_td = td.find_next_sibling("td")
                if next_td:
                    inp = next_td.find("input")
                    if inp and inp.get("value"):
                        return inp["value"]
                    match = re.search(r"[a-f0-9]{32,}", next_td.get_text(strip=True))
                    if match:
                        return match.group()
        # 备选
        text = soup.get_text()
        match = re.search(r"[a-f0-9]{32,}", text)
        return match.group() if match else ""

    async def get_uid_from_index(self) -> str:
        """从首页提取当前用户 UID"""
        soup = await self._get_page("index.php")
        link = soup.find("a", href=re.compile(r"userdetails\.php\?id=\d+"))
        if link:
            match = re.search(r"id=(\d+)", link.get("href", ""))
            if match:
                return match.group(1)
        return ""

    # ---- 种子搜索 ----

    async def search_torrents(self, params: SearchParams) -> list[TorrentInfo]:
        query = {}
        if params.keyword:
            query["search"] = params.keyword
        if params.category:
            query["cat"] = params.category
        if params.spstate:
            query["spstate"] = params.spstate
        if params.incldead:
            query["incldead"] = params.incldead
        if params.page:
            query["page"] = params.page
        soup = await self._get_page("torrents.php", query)
        return self._parse_torrent_list(soup)

    def _parse_torrent_list(self, soup: BeautifulSoup) -> list[TorrentInfo]:
        torrents = []
        table = soup.find("table", class_="torrents")
        if not table:
            logger.warning("未找到种子列表表格")
            return torrents
        rows = table.find_all("tr")[1:]
        seen_ids = set()
        for row in rows:
            try:
                torrent = self._parse_torrent_row(row)
                if torrent and torrent.id not in seen_ids:
                    torrents.append(torrent)
                    seen_ids.add(torrent.id)
            except Exception as e:
                logger.debug(f"解析种子行失败: {e}")
        logger.info(f"解析到 {len(torrents)} 个种子")
        return torrents

    def _parse_torrent_row(self, row: Tag) -> Optional[TorrentInfo]:
        """
        NicePT 实际结构（9 个直接子 td）：
        [0]分类 [1]标题(嵌套table) [2]评论 [3]时间 [4]大小 [5]做种 [6]下载 [7]完成 [8]发布者
        嵌套 table 内部行只有 3 个 embedded td，通过数量过滤。
        """
        top_tds = row.find_all("td", recursive=False)
        if len(top_tds) < 9:
            return None

        torrent = TorrentInfo()

        # 种子 ID 和标题
        title_link = row.find("a", href=re.compile(r"details\.php\?id=\d+"))
        if not title_link:
            return None
        match = re.search(r"id=(\d+)", title_link.get("href", ""))
        if not match:
            return None

        torrent.id = match.group(1)
        torrent.title = title_link.get("title", "") or title_link.get_text(strip=True)
        torrent.detail_url = f"{self.site_url}/details.php?id={torrent.id}"
        torrent.download_url = f"{self.site_url}/download.php?id={torrent.id}"

        # 副标题（<br/> 后面的文本）
        title_td = title_link.find_parent("td", class_="embedded")
        if title_td:
            for br in title_td.find_all("br"):
                nxt = br.next_sibling
                if nxt:
                    text = str(nxt).strip() if hasattr(nxt, "strip") else ""
                    if not text and hasattr(nxt, "get_text"):
                        text = nxt.get_text(strip=True)
                    if text and len(text) > 1:
                        torrent.subtitle = text
                        break

        # 分类
        cat_link = row.find("a", href=re.compile(r"\?cat=\d+"))
        if cat_link:
            cat_img = cat_link.find("img")
            if cat_img:
                torrent.category = cat_img.get("alt", "") or cat_img.get("title", "")

        # 促销
        torrent.discount_type = self._parse_discount(row)
        # H&R（重要：H&R 种子删种前必须满足做种要求，否则可能封号）
        torrent.has_hr = row.find("img", class_="hitandrun") is not None

        # 促销截止时间和免费状态
        torrent.is_free = torrent.discount_type in ("free", "twoupfree")
        promo_elem = row.find(class_=re.compile(r"pro_"))
        if promo_elem and title_td:
            # 促销截止时间在促销标签后面的 <span title="2026-02-22 17:34:02">
            for span in title_td.find_all("span", attrs={"title": True}):
                span_title = span.get("title", "")
                if re.match(r"\d{4}-\d{2}-\d{2}", span_title):
                    torrent.discount_end_time = span_title
                    break

        # 下载状态（进度条 div 的 title 属性，如 "seeding 100%"）
        if title_td:
            for div in title_td.find_all("div"):
                div_title = div.get("title", "")
                div_style = div.get("style", "")
                if "background-color" in div_style and "height" in div_style:
                    # 解析进度条 title，格式如 "seeding 100%", "downloading 45%"
                    m = re.match(r"(\w+)\s+([\d.]+)%?", div_title)
                    if m:
                        torrent.download_status = m.group(1)
                        torrent.download_progress = float(m.group(2))
                    else:
                        # 有进度条但无 title，从 style 解析
                        w = re.search(r"width:\s*([\d.]+)", div_style)
                        c = re.search(r"background-color:\s*(\w+)", div_style)
                        if w:
                            torrent.download_progress = float(w.group(1))
                        if c:
                            color = c.group(1).lower()
                            if color == "green":
                                torrent.download_status = "seeding"
                            elif color in ("red", "orange"):
                                torrent.download_status = "downloading"
                    break

        # 缩略图
        thumb = row.find("img", class_="nexus-lazy-load")
        if thumb:
            torrent.thumbnail = thumb.get("data-src", "") or thumb.get("src", "")

        # 数值列
        torrent.size = self._parse_size_text(top_tds[4].get_text(strip=True))
        torrent.seeders = self._parse_int(top_tds[5].get_text(strip=True))
        torrent.leechers = self._parse_int(top_tds[6].get_text(strip=True))
        torrent.completions = self._parse_int(top_tds[7].get_text(strip=True))
        torrent.uploader = top_tds[8].get_text(strip=True)

        return torrent

    # ---- 种子详情 ----

    async def get_torrent_detail(self, torrent_id: str) -> TorrentInfo:
        soup = await self._get_page("details.php", {"id": torrent_id})
        torrent = TorrentInfo(
            id=torrent_id,
            detail_url=f"{self.site_url}/details.php?id={torrent_id}",
            download_url=f"{self.site_url}/download.php?id={torrent_id}",
        )
        title_tag = soup.find("h1", id="top")
        if title_tag:
            torrent.title = title_tag.get_text(strip=True)
        for td in soup.find_all("td", class_="rowhead"):
            label = td.get_text(strip=True)
            next_td = td.find_next_sibling("td")
            if not next_td:
                continue
            val = next_td.get_text(strip=True)
            if "大小" in label or "尺寸" in label:
                torrent.size = self._parse_size_text(val)
            elif "類型" in label or "类型" in label or "分類" in label:
                torrent.category = val
        torrent.discount_type = self._parse_discount(soup)
        return torrent

    # ---- 下载种子文件 ----

    async def download_torrent(self, torrent_id: str, passkey: str = "") -> bytes:
        await self._rate_limit()
        client = await self._get_client()
        params = {"id": torrent_id}
        if passkey:
            params["passkey"] = passkey
        response = await client.get(f"{self.site_url}/download.php", params=params)
        response.raise_for_status()
        if "text/html" in response.headers.get("content-type", ""):
            raise Exception("下载失败，可能是权限不足或种子不存在")
        return response.content

    # ---- 收藏 ----

    async def get_bookmarks(self) -> list[TorrentInfo]:
        soup = await self._get_page("bookmarks.php")
        return self._parse_torrent_list(soup)

    # ---- 解析辅助 ----

    def _parse_discount(self, element: Tag) -> str:
        promo_map = {
            "pro_free2up": "twoupfree",
            "pro_free": "free",
            "pro_2up": "twoup",
            "pro_50pctdown": "halfdown",
            "pro_30pctdown": "thirtypercent",
            "pro_custom": "custom",
        }
        for cls_name, discount in promo_map.items():
            if element.find(class_=cls_name):
                return discount
        if element.find("font", class_="free"):
            return "free"
        return ""

    def _parse_transfer_text(self, text: str) -> tuple[float, float]:
        """
        解析 NicePT 用户详情页的传送行
        格式: '上傳量: 54.57 GB下載量: 0.00 KB實際上傳量: ...'
        只取前两个值（上传量和下载量）
        """
        uploaded = 0.0
        downloaded = 0.0
        # 上传量
        up_match = re.search(r"上[傳传]量[：:\s]*([\d,.]+\s*[TGMK]i?B)", text)
        if up_match:
            uploaded = self._parse_size_text(up_match.group(1))
        # 下载量
        down_match = re.search(r"下[載载]量[：:\s]*([\d,.]+\s*[TGMK]i?B)", text)
        if down_match:
            downloaded = self._parse_size_text(down_match.group(1))
        return uploaded, downloaded

    @staticmethod
    def _parse_size_text(text: str) -> float:
        text = text.strip()
        multipliers = {
            "TiB": 1024**4, "TB": 1024**4,
            "GiB": 1024**3, "GB": 1024**3,
            "MiB": 1024**2, "MB": 1024**2,
            "KiB": 1024, "KB": 1024,
            "B": 1,
        }
        for unit, mult in multipliers.items():
            match = re.search(rf"([\d,.]+)\s*{re.escape(unit)}", text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(",", "")) * mult
        return 0

    @staticmethod
    def _parse_int(text: str) -> int:
        text = text.replace(",", "").strip()
        match = re.search(r"\d+", text)
        return int(match.group()) if match else 0

    @staticmethod
    def _parse_number(text: str) -> float:
        text = text.replace(",", "").strip()
        match = re.search(r"[\d.]+", text)
        return float(match.group()) if match else 0

    @staticmethod
    def _parse_ratio(text: str) -> float:
        text = text.strip()
        if text in ("∞", "Inf", "inf", "無限", "无限"):
            return float("inf")
        match = re.search(r"[\d.]+", text.replace(",", ""))
        return float(match.group()) if match else 0

    # ---- H&R 考核 ----

    # 状态参数映射（NexusPHP myhr.php 的 status 参数）
    HR_STATUS_MAP = {
        1: "inspecting",
        2: "reached",
        3: "unreached",
        4: "pardoned",
    }

    async def get_hr_list(self, status: int = 1) -> list[HRRecord]:
        """
        获取 H&R 考核列表。
        status: 1=考核中, 2=已达标, 3=未达标, 4=已豁免
        """
        soup = await self._get_page("myhr.php", {"status": status})
        records = []
        table = soup.find("table", id="hr-table")
        if not table:
            # 兼容：有些站点没有 id，找包含 colhead 的表格
            for t in soup.find_all("table"):
                if t.find("td", class_="colhead"):
                    table = t
                    break
        if not table:
            logger.warning("未找到 H&R 表格")
            return records

        rows = table.find_all("tr")[1:]  # 跳过表头
        status_text = self.HR_STATUS_MAP.get(status, "inspecting")

        for row in rows:
            try:
                record = self._parse_hr_row(row, status_text)
                if record:
                    records.append(record)
            except Exception as e:
                logger.debug(f"解析 H&R 行失败: {e}")

        logger.info(f"解析到 {len(records)} 条 H&R 记录 (status={status})")
        return records

    def _parse_hr_row(self, row: Tag, status: str) -> Optional[HRRecord]:
        """
        解析 H&R 表格行。
        NexusPHP myhr.php 表格列顺序：
        [0]H&R ID [1]种子名称 [2]上传量 [3]下载量 [4]分享率
        [5]要求做种时间 [6]完成时间 [7]剩余考核时间 [8]备注 [9]操作
        """
        tds = row.find_all("td")
        if len(tds) < 8:
            return None

        record = HRRecord(status=status)

        # H&R ID
        hr_id_text = tds[0].get_text(strip=True)
        record.hr_id = self._parse_int(hr_id_text)
        if not record.hr_id:
            return None

        # 种子名称和 ID
        link = tds[1].find("a", href=re.compile(r"details\.php\?id=\d+"))
        if link:
            record.torrent_name = link.get_text(strip=True)
            match = re.search(r"id=(\d+)", link.get("href", ""))
            if match:
                record.torrent_id = match.group(1)

        # 上传量 / 下载量
        record.uploaded = self._parse_size_text(tds[2].get_text(strip=True))
        record.downloaded = self._parse_size_text(tds[3].get_text(strip=True))

        # 分享率
        record.share_ratio = self._parse_ratio(tds[4].get_text(strip=True))

        # 要求做种时间
        record.seed_time_required = tds[5].get_text(strip=True)

        # 完成时间
        record.completed_at = tds[6].get_text(strip=True)

        # 剩余考核时间
        record.inspect_time_left = tds[7].get_text(strip=True)

        # 备注（可能不存在）
        if len(tds) > 8:
            record.comment = tds[8].get_text(strip=True)

        return record

    async def remove_hit_and_run(self, hr_id: int) -> dict:
        """
        消除 H&R（花费魔力值）。
        通过 POST ajax.php 调用，模拟页面上的"消除"按钮。
        """
        await self._rate_limit()
        client = await self._get_client()
        url = f"{self.site_url}/ajax.php"
        try:
            response = await client.post(url, data={
                "action": "removeHitAndRun",
                "params[id]": str(hr_id),
            })
            data = response.json()
            if data.get("ret") == 0:
                logger.info(f"H&R {hr_id} 消除成功")
                return {"success": True, "message": "消除成功"}
            else:
                msg = data.get("msg", "未知错误")
                logger.warning(f"H&R {hr_id} 消除失败: {msg}")
                return {"success": False, "message": msg}
        except Exception as e:
            logger.error(f"H&R {hr_id} 消除请求失败: {e}")
            return {"success": False, "message": str(e)}
