"""
规则匹配引擎

根据 FilterRule 条件判断种子是否符合自动下载要求。
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from services.site_adapter import TorrentInfo

logger = logging.getLogger(__name__)


class RuleEngine:
    """规则匹配引擎"""

    @staticmethod
    def match(torrent: TorrentInfo, rule: dict) -> bool:
        """
        判断种子是否匹配规则

        参数:
            torrent: 种子信息
            rule: 规则字典（从 FilterRule 模型转换）

        返回:
            True 表示匹配，应该下载
        """
        # H&R 过滤（跳过 H&R 种子，避免做种压力导致封号）
        if rule.get("skip_hr") and torrent.has_hr:
            logger.debug(f"种子 {torrent.id} 是 H&R 种子，规则要求跳过")
            return False

        # 促销条件
        if rule.get("free_only") and torrent.discount_type not in ("free", "twoupfree"):
            logger.debug(f"种子 {torrent.id} 不满足免费条件")
            return False

        if rule.get("double_upload") and torrent.discount_type not in ("twoup", "twoupfree"):
            logger.debug(f"种子 {torrent.id} 不满足双倍上传条件")
            return False

        # 大小限制
        if rule.get("min_size") and torrent.size < rule["min_size"]:
            return False
        if rule.get("max_size") and torrent.size > rule["max_size"]:
            return False

        # 做种人数
        if rule.get("min_seeders") is not None and torrent.seeders < rule["min_seeders"]:
            return False
        if rule.get("max_seeders") is not None and torrent.seeders > rule["max_seeders"]:
            return False

        # 下载人数
        if rule.get("min_leechers") is not None and torrent.leechers < rule["min_leechers"]:
            return False
        if rule.get("max_leechers") is not None and torrent.leechers > rule["max_leechers"]:
            return False

        # 关键词匹配
        if rule.get("keywords"):
            keywords = [k.strip() for k in rule["keywords"].split(",") if k.strip()]
            title_text = f"{torrent.title} {torrent.subtitle}".lower()
            if not any(kw.lower() in title_text for kw in keywords):
                return False

        # 排除关键词
        if rule.get("exclude_keywords"):
            excludes = [k.strip() for k in rule["exclude_keywords"].split(",") if k.strip()]
            title_text = f"{torrent.title} {torrent.subtitle}".lower()
            if any(kw.lower() in title_text for kw in excludes):
                return False

        # 分类过滤
        if rule.get("categories"):
            cats = [c.strip() for c in rule["categories"].split(",") if c.strip()]
            if torrent.category and torrent.category not in cats:
                return False

        # 发布时间限制
        if rule.get("max_publish_hours") and torrent.upload_time:
            max_age = timedelta(hours=rule["max_publish_hours"])
            if datetime.utcnow() - torrent.upload_time > max_age:
                return False

        logger.info(f"种子 {torrent.id} [{torrent.title}] 匹配规则")
        return True

    @staticmethod
    def is_duplicate(torrent_id: str, existing_ids: set[str]) -> bool:
        """检查是否已下载过"""
        return torrent_id in existing_ids
