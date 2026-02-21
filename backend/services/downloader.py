"""
下载器适配器

统一接口支持 qBittorrent 和 Transmission。
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class DownloaderStats:
    """下载器统计信息"""
    download_speed: int = 0  # 字节/秒
    upload_speed: int = 0
    downloading_count: int = 0
    seeding_count: int = 0
    free_space: int = 0  # 字节
    total_space: int = 0


@dataclass
class TorrentStatus:
    """下载器中的种子状态"""
    info_hash: str = ""
    name: str = ""
    size: int = 0
    progress: float = 0
    status: str = ""  # downloading / seeding / paused / completed / error
    state: str = ""   # 同 status，用于状态同步
    download_speed: int = 0
    upload_speed: int = 0
    tags: str = ""
    save_path: str = ""
    tracker_msg: str = ""  # tracker 返回的消息，用于检测 unregistered
    total_size: int = 0


class BaseDownloader(ABC):
    """下载器基类"""

    def __init__(self, host: str, port: int, username: str = "", password: str = "", use_ssl: bool = False):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.scheme = "https" if use_ssl else "http"
        self.base_url = f"{self.scheme}://{self.host}:{self.port}"

    @abstractmethod
    async def test_connection(self) -> bool:
        """测试连接"""
        pass

    @abstractmethod
    async def add_torrent(self, torrent_data: bytes, save_path: str = "", tags: str = "") -> str:
        """添加种子，返回 info_hash"""
        pass

    @abstractmethod
    async def remove_torrent(self, info_hash: str, delete_files: bool = False) -> bool:
        """删除种子"""
        pass

    @abstractmethod
    async def pause_torrent(self, info_hash: str) -> bool:
        """暂停种子"""
        pass

    @abstractmethod
    async def get_torrent_status(self, info_hash: str) -> Optional[TorrentStatus]:
        """获取种子状态"""
        pass

    @abstractmethod
    async def get_all_torrents(self) -> list[TorrentStatus]:
        """获取所有种子"""
        pass

    @abstractmethod
    async def get_stats(self) -> DownloaderStats:
        """获取下载器统计"""
        pass

    @abstractmethod
    async def get_tags(self) -> list[str]:
        """获取所有标签"""
        pass

    @abstractmethod
    async def create_tag(self, tag: str) -> bool:
        """创建标签"""
        pass


class QBittorrentAdapter(BaseDownloader):
    """qBittorrent 适配器"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._client: Optional[httpx.AsyncClient] = None
        self._sid: str = ""

    async def _get_client(self) -> httpx.AsyncClient:
        """获取已认证的客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15, verify=False)
            await self._login()
        return self._client

    async def _login(self):
        """登录 qBittorrent Web UI"""
        url = f"{self.base_url}/api/v2/auth/login"
        response = await self._client.post(url, data={
            "username": self.username,
            "password": self.password,
        })
        if response.text.strip() != "Ok.":
            raise Exception("qBittorrent 登录失败")
        # 保存 SID cookie
        self._sid = response.cookies.get("SID", "")
        self._client.cookies.set("SID", self._sid)
        logger.info("qBittorrent 登录成功")

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            resp = await client.get(f"{self.base_url}/api/v2/app/version")
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"qBittorrent 连接测试失败: {e}")
            return False

    async def add_torrent(self, torrent_data: bytes, save_path: str = "", tags: str = "") -> str:
        client = await self._get_client()
        files = {"torrents": ("torrent.torrent", torrent_data, "application/x-bittorrent")}
        data = {}
        if save_path:
            data["savepath"] = save_path
        if tags:
            data["tags"] = tags

        resp = await client.post(f"{self.base_url}/api/v2/torrents/add", files=files, data=data)
        if resp.text.strip() != "Ok.":
            raise Exception(f"添加种子失败: {resp.text}")
        logger.info("种子已添加到 qBittorrent")
        return ""  # qB 不直接返回 hash，需要后续查询

    async def remove_torrent(self, info_hash: str, delete_files: bool = False) -> bool:
        client = await self._get_client()
        resp = await client.post(f"{self.base_url}/api/v2/torrents/delete", data={
            "hashes": info_hash,
            "deleteFiles": str(delete_files).lower(),
        })
        return resp.status_code == 200

    async def pause_torrent(self, info_hash: str) -> bool:
        """暂停种子（qBittorrent API v2）"""
        client = await self._get_client()
        resp = await client.post(f"{self.base_url}/api/v2/torrents/pause", data={
            "hashes": info_hash,
        })
        return resp.status_code == 200

    async def get_torrent_status(self, info_hash: str) -> Optional[TorrentStatus]:
        client = await self._get_client()
        resp = await client.get(f"{self.base_url}/api/v2/torrents/info", params={"hashes": info_hash})
        data = resp.json()
        if not data:
            return None
        t = data[0]
        mapped = self._map_state(t["state"])
        return TorrentStatus(
            info_hash=t["hash"],
            name=t["name"],
            size=t["size"],
            total_size=t.get("total_size", t["size"]),
            progress=t["progress"],
            status=mapped,
            state=mapped,
            download_speed=t.get("dlspeed", 0),
            upload_speed=t.get("upspeed", 0),
            tags=t.get("tags", ""),
            save_path=t.get("save_path", ""),
            tracker_msg=t.get("tracker_msg", ""),
        )

    async def get_all_torrents(self) -> list[TorrentStatus]:
        client = await self._get_client()
        resp = await client.get(f"{self.base_url}/api/v2/torrents/info")
        results = []
        for t in resp.json():
            mapped = self._map_state(t["state"])
            results.append(TorrentStatus(
                info_hash=t["hash"],
                name=t["name"],
                size=t["size"],
                total_size=t.get("total_size", t["size"]),
                progress=t["progress"],
                status=mapped,
                state=mapped,
                download_speed=t.get("dlspeed", 0),
                upload_speed=t.get("upspeed", 0),
                tags=t.get("tags", ""),
                save_path=t.get("save_path", ""),
                tracker_msg=t.get("tracker_msg", ""),
            ))
        return results

    async def get_stats(self) -> DownloaderStats:
        client = await self._get_client()
        resp = await client.get(f"{self.base_url}/api/v2/transfer/info")
        info = resp.json()
        torrents = await self.get_all_torrents()
        return DownloaderStats(
            download_speed=info.get("dl_info_speed", 0),
            upload_speed=info.get("up_info_speed", 0),
            downloading_count=sum(1 for t in torrents if t.status == "downloading"),
            seeding_count=sum(1 for t in torrents if t.status == "seeding"),
        )

    async def get_tags(self) -> list[str]:
        client = await self._get_client()
        resp = await client.get(f"{self.base_url}/api/v2/torrents/tags")
        return resp.json()

    async def create_tag(self, tag: str) -> bool:
        client = await self._get_client()
        resp = await client.post(f"{self.base_url}/api/v2/torrents/createTags", data={"tags": tag})
        return resp.status_code == 200

    @staticmethod
    def _map_state(state: str) -> str:
        """映射 qBittorrent 状态到统一状态"""
        mapping = {
            "downloading": "downloading",
            "stalledDL": "downloading",
            "metaDL": "downloading",
            "forcedDL": "downloading",
            "uploading": "seeding",
            "stalledUP": "seeding",
            "forcedUP": "seeding",
            "pausedDL": "paused",
            "pausedUP": "paused",
            "queuedDL": "downloading",
            "queuedUP": "seeding",
            "error": "error",
            "missingFiles": "error",
        }
        return mapping.get(state, "unknown")


class TransmissionAdapter(BaseDownloader):
    """Transmission 适配器"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._session_id = ""
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15, verify=False)
        return self._client

    async def _rpc_call(self, method: str, arguments: dict = None) -> dict:
        """调用 Transmission RPC"""
        client = await self._get_client()
        url = f"{self.base_url}/transmission/rpc"
        payload = {"method": method}
        if arguments:
            payload["arguments"] = arguments

        headers = {}
        if self._session_id:
            headers["X-Transmission-Session-Id"] = self._session_id
        if self.username:
            import base64
            cred = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers["Authorization"] = f"Basic {cred}"

        resp = await client.post(url, json=payload, headers=headers)

        # Transmission 返回 409 时需要更新 session ID
        if resp.status_code == 409:
            self._session_id = resp.headers.get("X-Transmission-Session-Id", "")
            headers["X-Transmission-Session-Id"] = self._session_id
            resp = await client.post(url, json=payload, headers=headers)

        resp.raise_for_status()
        return resp.json()

    async def test_connection(self) -> bool:
        try:
            result = await self._rpc_call("session-get")
            return result.get("result") == "success"
        except Exception as e:
            logger.error(f"Transmission 连接测试失败: {e}")
            return False

    async def add_torrent(self, torrent_data: bytes, save_path: str = "", tags: str = "") -> str:
        import base64
        args = {"metainfo": base64.b64encode(torrent_data).decode()}
        if save_path:
            args["download-dir"] = save_path
        result = await self._rpc_call("torrent-add", args)
        if result.get("result") != "success":
            raise Exception(f"添加种子失败: {result}")
        added = result.get("arguments", {}).get("torrent-added", {})
        return added.get("hashString", "")

    async def remove_torrent(self, info_hash: str, delete_files: bool = False) -> bool:
        # 先通过 hash 找到 torrent ID
        all_torrents = await self._rpc_call("torrent-get", {
            "fields": ["id", "hashString"]
        })
        torrents = all_torrents.get("arguments", {}).get("torrents", [])
        tid = None
        for t in torrents:
            if t.get("hashString", "").lower() == info_hash.lower():
                tid = t["id"]
                break
        if tid is None:
            return False

        result = await self._rpc_call("torrent-remove", {
            "ids": [tid],
            "delete-local-data": delete_files,
        })
        return result.get("result") == "success"

    async def pause_torrent(self, info_hash: str) -> bool:
        """暂停种子（Transmission RPC）"""
        all_torrents = await self._rpc_call("torrent-get", {
            "fields": ["id", "hashString"]
        })
        torrents = all_torrents.get("arguments", {}).get("torrents", [])
        tid = None
        for t in torrents:
            if t.get("hashString", "").lower() == info_hash.lower():
                tid = t["id"]
                break
        if tid is None:
            return False
        result = await self._rpc_call("torrent-stop", {"ids": [tid]})
        return result.get("result") == "success"

    async def get_torrent_status(self, info_hash: str) -> Optional[TorrentStatus]:
        all_t = await self.get_all_torrents()
        for t in all_t:
            if t.info_hash.lower() == info_hash.lower():
                return t
        return None

    async def get_all_torrents(self) -> list[TorrentStatus]:
        result = await self._rpc_call("torrent-get", {
            "fields": ["id", "hashString", "name", "totalSize", "percentDone",
                        "status", "rateDownload", "rateUpload", "downloadDir",
                        "trackerStats", "labels"]
        })
        torrents = result.get("arguments", {}).get("torrents", [])
        results = []
        for t in torrents:
            mapped = self._map_status(t["status"])
            # 提取 tracker 消息
            tracker_msg = ""
            tracker_stats = t.get("trackerStats", [])
            if tracker_stats:
                tracker_msg = tracker_stats[0].get("lastAnnounceResult", "")
            results.append(TorrentStatus(
                info_hash=t["hashString"],
                name=t["name"],
                size=t["totalSize"],
                total_size=t["totalSize"],
                progress=t["percentDone"],
                status=mapped,
                state=mapped,
                download_speed=t.get("rateDownload", 0),
                upload_speed=t.get("rateUpload", 0),
                save_path=t.get("downloadDir", ""),
                tracker_msg=tracker_msg,
                tags=",".join(t.get("labels", [])),
            ))
        return results

    async def get_stats(self) -> DownloaderStats:
        result = await self._rpc_call("session-stats")
        stats = result.get("arguments", {})
        current = stats.get("current-stats", {})
        return DownloaderStats(
            download_speed=stats.get("downloadSpeed", 0),
            upload_speed=stats.get("uploadSpeed", 0),
        )

    async def get_tags(self) -> list[str]:
        # Transmission 不原生支持标签
        return []

    async def create_tag(self, tag: str) -> bool:
        return False

    @staticmethod
    def _map_status(status: int) -> str:
        mapping = {0: "paused", 1: "downloading", 2: "downloading",
                   3: "downloading", 4: "seeding", 5: "seeding", 6: "seeding"}
        return mapping.get(status, "unknown")


def create_downloader(dtype: str, **kwargs) -> BaseDownloader:
    """工厂方法：创建下载器实例"""
    if dtype == "qbittorrent":
        return QBittorrentAdapter(**kwargs)
    elif dtype == "transmission":
        return TransmissionAdapter(**kwargs)
    else:
        raise ValueError(f"不支持的下载器类型: {dtype}")
