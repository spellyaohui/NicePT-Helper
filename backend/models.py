"""SQLAlchemy 数据模型"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime, JSON, ForeignKey
)
from database import Base


class User(Base):
    """系统登录用户"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Account(Base):
    """PT 站账号"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_name = Column(String(50), default="NicePT")
    site_url = Column(String(255), nullable=False)
    username = Column(String(100), nullable=False)
    cookie = Column(Text, nullable=False)  # NexusPHP 使用 Cookie 认证
    passkey = Column(String(100), default="")
    uid = Column(String(50), default="")  # 站点用户 ID

    # 统计字段
    uploaded = Column(Float, default=0)  # 上传量（字节）
    downloaded = Column(Float, default=0)  # 下载量（字节）
    ratio = Column(Float, default=0)  # 分享率
    bonus = Column(Float, default=0)  # 魔力值
    user_class = Column(String(50), default="")  # 用户等级

    is_active = Column(Boolean, default=True)
    last_refresh = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FilterRule(Base):
    """自动下载规则"""
    __tablename__ = "filter_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True)
    rule_type = Column(String(20), default="normal")  # normal / favorite
    sort_order = Column(Integer, default=0)

    # 促销条件
    free_only = Column(Boolean, default=False)
    double_upload = Column(Boolean, default=False)

    # H&R 控制（跳过 H&R 种子，避免做种压力）
    skip_hr = Column(Boolean, default=False)

    # 大小限制（字节）
    min_size = Column(Float, nullable=True)
    max_size = Column(Float, nullable=True)

    # 做种/下载人数限制
    min_seeders = Column(Integer, nullable=True)
    max_seeders = Column(Integer, nullable=True)
    min_leechers = Column(Integer, nullable=True)
    max_leechers = Column(Integer, nullable=True)

    # 关键词过滤
    keywords = Column(Text, default="")  # 逗号分隔
    exclude_keywords = Column(Text, default="")  # 逗号分隔

    # 分类过滤
    categories = Column(Text, default="")  # 逗号分隔的分类 ID

    # 发布时间限制（小时）
    max_publish_hours = Column(Integer, nullable=True)

    # 下载控制
    max_downloading = Column(Integer, default=5)  # 最大同时下载数
    downloader_id = Column(Integer, ForeignKey("downloaders.id"), nullable=True)
    save_path = Column(String(500), default="")
    tags = Column(String(255), default="")

    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Downloader(Base):
    """下载器配置"""
    __tablename__ = "downloaders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)  # qbittorrent / transmission
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(100), default="")
    password = Column(String(255), default="")
    use_ssl = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class DownloadHistory(Base):
    """下载历史记录"""
    __tablename__ = "download_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    torrent_id = Column(String(50), nullable=False, index=True)  # 站点种子 ID
    info_hash = Column(String(64), default="")
    title = Column(String(500), nullable=False)
    size = Column(Float, default=0)

    # 状态：downloading / seeding / completed / deleted / expired_deleted / dynamic_deleted
    status = Column(String(30), default="downloading")

    # 促销信息
    discount_type = Column(String(20), default="")  # free / twoup / twoupfree / halfdown / twouphalfdown / thirtypercent
    discount_end_time = Column(DateTime, nullable=True)

    # H&R 标记（重要：H&R 种子在做种达标前绝不能删除，否则可能封号）
    has_hr = Column(Boolean, default=False)

    # 关联
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    downloader_id = Column(Integer, ForeignKey("downloaders.id"), nullable=True)
    rule_id = Column(Integer, ForeignKey("filter_rules.id"), nullable=True)

    # 收藏相关
    is_favorited = Column(Boolean, default=False)

    # 下载器中的标签
    tags = Column(String(255), default="")
    save_path = Column(String(500), default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SystemSetting(Base):
    """系统设置（键值对存储）"""
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HitAndRun(Base):
    """H&R 考核记录（从站点 myhr.php 同步）"""
    __tablename__ = "hit_and_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hr_id = Column(Integer, unique=True, nullable=False, index=True)  # 站点 H&R ID
    torrent_id = Column(String(50), nullable=False, index=True)
    torrent_name = Column(String(500), default="")
    uploaded = Column(Float, default=0)       # 该种子上传量（字节）
    downloaded = Column(Float, default=0)     # 该种子下载量（字节）
    share_ratio = Column(Float, default=0)    # 分享率
    seed_time_required = Column(String(100), default="")  # 还需做种时间（文本）
    completed_at = Column(String(50), default="")         # 下载完成时间
    inspect_time_left = Column(String(100), default="")   # 剩余考核时间（文本）
    comment = Column(Text, default="")        # 备注

    # 状态: inspecting / reached / unreached / pardoned
    status = Column(String(20), default="inspecting")

    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StatsSnapshot(Base):
    """统计快照（用于趋势图）"""
    __tablename__ = "stats_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    uploaded = Column(Float, default=0)       # 累计上传（字节）
    downloaded = Column(Float, default=0)     # 累计下载（字节）
    upload_speed = Column(Float, default=0)   # 当前上传速率（字节/秒）
    download_speed = Column(Float, default=0) # 当前下载速率（字节/秒）
    created_at = Column(DateTime, default=datetime.utcnow)
