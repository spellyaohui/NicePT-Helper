"""
调度服务

管理定时任务：自动下载、过期检查、状态同步、账号刷新等。
支持精确到期定时器（每个种子独立）和保底遍历定时器。
"""
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def init_scheduler():
    """初始化调度器"""
    if not scheduler.running:
        scheduler.start()
        logger.info("调度器已启动")


def shutdown_scheduler():
    """关闭调度器"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("调度器已关闭")


def add_job(func, trigger: str, job_id: str, **kwargs):
    """添加或替换定时任务"""
    existing = scheduler.get_job(job_id)
    if existing:
        scheduler.remove_job(job_id)
    scheduler.add_job(func, trigger, id=job_id, replace_existing=True, **kwargs)
    logger.info(f"已添加定时任务: {job_id}")


def remove_job(job_id: str):
    """移除定时任务"""
    existing = scheduler.get_job(job_id)
    if existing:
        scheduler.remove_job(job_id)
        logger.info(f"已移除定时任务: {job_id}")


def get_scheduler_status() -> dict:
    """获取调度器状态"""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": str(job.next_run_time) if job.next_run_time else None,
        })
    return {"running": scheduler.running, "jobs": jobs}


async def restore_interval_jobs():
    """
    恢复所有“间隔型（interval）”任务。

    说明：
    - 这些任务由前端【定时任务开关】与【刷新间隔】控制。
    - 每个种子“促销到期”的精确任务属于 date trigger（单种子定时器），
      不在这里恢复，应由 restore_expiry_jobs() 恢复。
    """
    from database import async_session
    from models import SystemSetting

    # 这些默认值需要与前端保持一致
    default_intervals = {
        "auto_download_minutes": 10,
        "account_refresh_minutes": 60,
        "status_sync_minutes": 5,
        "expired_check_minutes": 30,
        "dynamic_delete_minutes": 10,
        "unregistered_check_minutes": 10,
    }

    default_control = {
        "auto_download_enabled": False,
        "account_refresh_enabled": False,
        "status_sync_enabled": False,
        "expired_check_enabled": False,
        "dynamic_delete_enabled": False,
        "unregistered_check_enabled": False,
    }

    async with async_session() as db:
        # 读取刷新间隔
        interval_setting = (await db.execute(
            select(SystemSetting).where(SystemSetting.key == "refresh_intervals")
        )).scalar_one_or_none()
        intervals = interval_setting.value if interval_setting and interval_setting.value else default_intervals

        # 兜底补全缺失字段
        for k, v in default_intervals.items():
            intervals.setdefault(k, v)

        # 读取调度开关
        control_setting = (await db.execute(
            select(SystemSetting).where(SystemSetting.key == "schedule_control")
        )).scalar_one_or_none()
        control = control_setting.value if control_setting and control_setting.value else default_control

        for k, v in default_control.items():
            control.setdefault(k, v)

    # 统计快照采集：固定任务，不暴露给开关
    add_job(collect_stats_snapshot, "interval", "stats_snapshot", minutes=10, name="统计快照采集")

    # 根据开关注册/移除任务
    if control.get("auto_download_enabled"):
        add_job(auto_download_torrents, "interval", "auto_download",
                minutes=intervals.get("auto_download_minutes", 10), name="自动下载")
    else:
        remove_job("auto_download")

    if control.get("account_refresh_enabled"):
        add_job(refresh_all_accounts, "interval", "account_refresh",
                minutes=intervals.get("account_refresh_minutes", 60), name="账号刷新")
    else:
        remove_job("account_refresh")

    if control.get("status_sync_enabled"):
        add_job(sync_download_status, "interval", "status_sync",
                minutes=intervals.get("status_sync_minutes", 5), name="状态同步")
    else:
        remove_job("status_sync")

    if control.get("expired_check_enabled"):
        add_job(check_expired_torrents, "interval", "expired_check",
                minutes=intervals.get("expired_check_minutes", 30), name="过期检查（兜底）")
    else:
        remove_job("expired_check")

    if control.get("dynamic_delete_enabled"):
        add_job(check_dynamic_delete, "interval", "dynamic_delete",
                minutes=intervals.get("dynamic_delete_minutes", 10), name="动态删种")
    else:
        remove_job("dynamic_delete")

    if control.get("unregistered_check_enabled"):
        add_job(check_unregistered_torrents, "interval", "unregistered_check",
                minutes=intervals.get("unregistered_check_minutes", 10), name="失效种子检查")
    else:
        remove_job("unregistered_check")


# ========== 精确到期定时器 ==========

def schedule_expiry_job(history_id: int, torrent_id: str, expire_time: datetime):
    """
    为单个种子注册精确到期定时任务。
    到期时间到达后自动执行 handle_single_expiry。
    提前 1 分钟触发，留出执行余量。
    """
    job_id = f"expiry_{history_id}"
    # 如果已有同 ID 任务，先移除
    existing = scheduler.get_job(job_id)
    if existing:
        scheduler.remove_job(job_id)

    # 确保触发时间在未来（至少 10 秒后）
    run_time = expire_time - timedelta(minutes=1)
    now = datetime.utcnow()
    if run_time <= now:
        run_time = now + timedelta(seconds=10)

    scheduler.add_job(
        handle_single_expiry,
        trigger="date",
        run_date=run_time,
        id=job_id,
        args=[history_id],
        name=f"到期处理: 种子 {torrent_id}",
        replace_existing=True,
        misfire_grace_time=300,  # 允许 5 分钟的延迟执行
    )
    logger.info(f"已注册精确到期任务: {job_id}, 触发时间: {run_time}")


async def handle_single_expiry(history_id: int):
    """
    处理单个种子到期。
    根据设置决定删除还是暂停，H&R 种子强制暂停。
    """
    from database import async_session
    from models import DownloadHistory, Downloader, SystemSetting
    from services.downloader import create_downloader

    async with async_session() as db:
        result = await db.execute(
            select(DownloadHistory).where(DownloadHistory.id == history_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            logger.warning(f"到期处理: 历史记录 {history_id} 不存在")
            return

        # 已经是终态，跳过
        if record.status not in ("downloading", "seeding"):
            logger.debug(f"种子 [{record.torrent_id}] 状态为 {record.status}，跳过到期处理")
            return

        # 检查是否真的过期了
        if record.discount_end_time and record.discount_end_time > datetime.utcnow():
            logger.debug(f"种子 [{record.torrent_id}] 尚未过期，跳过")
            return

        # 读取到期动作设置
        setting_result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == "auto_delete")
        )
        setting = setting_result.scalar_one_or_none()
        config = setting.value if setting else {}

        # 主开关关闭时：不做任何到期保护动作（暂停/删除都不执行）
        # 重要警示：关闭后可能错过免费到期时间点，带来账号风险，请在 README 中特别标注。
        if not config.get("enabled") or not config.get("delete_expired"):
            logger.warning(f"促销到期保护已关闭，跳过处理: [{record.torrent_id}] {record.title[:40]}")
            return

        # expired_action: "delete" 删除 / "pause" 暂停，默认 "delete"
        expired_action = config.get("expired_action", "delete")

        # H&R 种子强制暂停，绝不删除
        if record.has_hr:
            expired_action = "pause"
            logger.warning(f"种子 [{record.torrent_id}] 是 H&R 种子，强制暂停（不删除）")

        if not record.downloader_id or not record.info_hash:
            logger.warning(f"种子 [{record.torrent_id}] 缺少下载器信息，仅更新状态")
            record.status = "expired_paused" if expired_action == "pause" else "expired_deleted"
            await db.commit()
            return

        dl_result = await db.execute(
            select(Downloader).where(Downloader.id == record.downloader_id)
        )
        dl_model = dl_result.scalar_one_or_none()
        if not dl_model:
            logger.warning(f"种子 [{record.torrent_id}] 的下载器不存在")
            return

        downloader = create_downloader(
            dl_model.type, host=dl_model.host, port=dl_model.port,
            username=dl_model.username, password=dl_model.password, use_ssl=dl_model.use_ssl,
        )

        try:
            if expired_action == "pause":
                await downloader.pause_torrent(record.info_hash)
                record.status = "expired_paused"
                logger.info(f"促销到期暂停: [{record.torrent_id}] {record.title[:40]}")
            else:
                await downloader.remove_torrent(record.info_hash, delete_files=True)
                record.status = "expired_deleted"
                logger.info(f"促销到期删种: [{record.torrent_id}] {record.title[:40]}")
        except Exception as e:
            logger.error(f"到期处理种子 [{record.torrent_id}] 失败: {e}")

        await db.commit()


async def restore_expiry_jobs():
    """
    启动时恢复所有未过期种子的精确定时任务。
    遍历所有活跃的、有 discount_end_time 的下载记录。
    """
    from database import async_session
    from models import DownloadHistory

    async with async_session() as db:
        result = await db.execute(
            select(DownloadHistory).where(
                DownloadHistory.discount_end_time != None,
                DownloadHistory.status.in_(["downloading", "seeding"]),
            )
        )
        records = result.scalars().all()
        count = 0
        for record in records:
            schedule_expiry_job(record.id, record.torrent_id, record.discount_end_time)
            count += 1

        if count > 0:
            logger.info(f"已恢复 {count} 个精确到期定时任务")


# ========== 定时任务实现 ==========

async def _get_db_session():
    """获取数据库会话"""
    from database import async_session
    async with async_session() as session:
        yield session


async def auto_download_torrents():
    """
    自动下载任务：
    1. 读取所有启用的规则（按 sort_order）
    2. 对每条规则，用关联账号搜索种子
    3. 过滤已下载的种子
    4. 规则匹配
    5. 推送到下载器并记录历史
    """
    from database import async_session
    from models import FilterRule, Account, Downloader, DownloadHistory
    from services.site_adapter import NexusPHPAdapter, SearchParams
    from services.rule_engine import RuleEngine
    from services.downloader import create_downloader

    logger.info("开始执行自动下载任务")

    async with async_session() as db:
        # 获取所有启用的规则
        result = await db.execute(
            select(FilterRule).where(FilterRule.enabled == True).order_by(FilterRule.sort_order)
        )
        rules = result.scalars().all()
        if not rules:
            logger.info("没有启用的规则，跳过")
            return

        # 获取已下载的种子 ID 集合
        hist_result = await db.execute(select(DownloadHistory.torrent_id))
        downloaded_ids = {row[0] for row in hist_result.all()}

        for rule in rules:
            try:
                await _process_rule(db, rule, downloaded_ids)
            except Exception as e:
                logger.error(f"处理规则 [{rule.name}] 失败: {e}")

    logger.info("自动下载任务完成")


async def _process_rule(db, rule, downloaded_ids: set):
    """处理单条规则"""
    from models import Account, Downloader, DownloadHistory
    from services.site_adapter import NexusPHPAdapter, SearchParams
    from services.rule_engine import RuleEngine
    from services.downloader import create_downloader

    # 确定使用的账号
    account_id = rule.account_id
    if not account_id:
        # 没有指定账号，使用第一个活跃账号
        result = await db.execute(
            select(Account).where(Account.is_active == True).limit(1)
        )
        account = result.scalar_one_or_none()
        if not account:
            logger.warning(f"规则 [{rule.name}] 没有可用账号")
            return
    else:
        result = await db.execute(select(Account).where(Account.id == account_id))
        account = result.scalar_one_or_none()
        if not account:
            logger.warning(f"规则 [{rule.name}] 指定的账号 {account_id} 不存在")
            return

    # 确定下载器
    if not rule.downloader_id:
        logger.warning(f"规则 [{rule.name}] 未指定下载器，跳过")
        return
    dl_result = await db.execute(select(Downloader).where(Downloader.id == rule.downloader_id))
    dl_model = dl_result.scalar_one_or_none()
    if not dl_model:
        logger.warning(f"规则 [{rule.name}] 指定的下载器不存在")
        return

    # 检查当前下载中的数量
    from sqlalchemy import func
    count_result = await db.execute(
        select(func.count()).select_from(DownloadHistory).where(
            DownloadHistory.rule_id == rule.id,
            DownloadHistory.status == "downloading",
        )
    )
    current_downloading = count_result.scalar() or 0
    if current_downloading >= rule.max_downloading:
        logger.info(f"规则 [{rule.name}] 已达最大下载数 {rule.max_downloading}，跳过")
        return

    # 构建搜索参数
    params = SearchParams(
        keyword=rule.keywords.split(",")[0].strip() if rule.keywords else "",
    )
    # 免费筛选
    if rule.free_only:
        params.spstate = 2

    adapter = NexusPHPAdapter(account.site_url, account.cookie)
    try:
        torrents = await adapter.search_torrents(params)
    finally:
        await adapter.close()

    # 转换规则为字典
    rule_dict = {
        "free_only": rule.free_only,
        "double_upload": rule.double_upload,
        "skip_hr": rule.skip_hr,
        "min_size": rule.min_size,
        "max_size": rule.max_size,
        "min_seeders": rule.min_seeders,
        "max_seeders": rule.max_seeders,
        "min_leechers": rule.min_leechers,
        "max_leechers": rule.max_leechers,
        "keywords": rule.keywords,
        "exclude_keywords": rule.exclude_keywords,
        "categories": rule.categories,
        "max_publish_hours": rule.max_publish_hours,
    }

    engine = RuleEngine()
    downloader = create_downloader(
        dl_model.type, host=dl_model.host, port=dl_model.port,
        username=dl_model.username, password=dl_model.password, use_ssl=dl_model.use_ssl,
    )

    slots = rule.max_downloading - current_downloading
    added = 0

    for torrent in torrents:
        if added >= slots:
            break

        # 跳过已下载
        if torrent.id in downloaded_ids:
            continue

        # 规则匹配
        if not engine.match(torrent, rule_dict):
            continue

        # 下载并推送
        try:
            adapter2 = NexusPHPAdapter(account.site_url, account.cookie)
            try:
                torrent_data = await adapter2.download_torrent(torrent.id, account.passkey)
            finally:
                await adapter2.close()

            info_hash = await downloader.add_torrent(
                torrent_data, save_path=rule.save_path, tags=rule.tags,
            )

            # 记录历史（保存 H&R 和促销截止时间，用于后续保护和自动删种判断）
            # 解析 discount_end_time 字符串为 datetime
            _discount_end = None
            if torrent.discount_end_time:
                try:
                    _discount_end = datetime.strptime(torrent.discount_end_time, "%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    pass

            history = DownloadHistory(
                torrent_id=torrent.id,
                info_hash=info_hash,
                title=torrent.title,
                size=torrent.size,
                status="downloading",
                discount_type=torrent.discount_type,
                discount_end_time=_discount_end,
                has_hr=torrent.has_hr,
                account_id=account.id,
                downloader_id=dl_model.id,
                rule_id=rule.id,
                tags=rule.tags,
                save_path=rule.save_path,
            )
            db.add(history)
            await db.commit()

            # 如果有促销截止时间，注册精确到期定时任务
            if _discount_end:
                await db.refresh(history)  # 获取自增 ID
                schedule_expiry_job(history.id, torrent.id, _discount_end)

            downloaded_ids.add(torrent.id)
            added += 1
            logger.info(f"自动下载: [{torrent.id}] {torrent.title[:60]}")

        except Exception as e:
            logger.error(f"下载种子 {torrent.id} 失败: {e}")

    if added > 0:
        logger.info(f"规则 [{rule.name}] 本次下载 {added} 个种子")


async def refresh_all_accounts():
    """刷新所有活跃账号的数据"""
    from database import async_session
    from models import Account
    from services.site_adapter import NexusPHPAdapter

    logger.info("开始刷新所有账号数据")

    async with async_session() as db:
        result = await db.execute(select(Account).where(Account.is_active == True))
        accounts = result.scalars().all()

        for account in accounts:
            try:
                if not account.uid:
                    continue
                adapter = NexusPHPAdapter(account.site_url, account.cookie)
                try:
                    stats = await adapter.get_user_stats(account.uid)
                    account.uploaded = stats.uploaded
                    account.downloaded = stats.downloaded
                    account.ratio = stats.ratio
                    account.bonus = stats.bonus
                    account.user_class = stats.user_class
                    if stats.passkey:
                        account.passkey = stats.passkey
                    account.last_refresh = datetime.utcnow()
                finally:
                    await adapter.close()
                logger.info(f"账号 [{account.username}] 刷新成功")
            except Exception as e:
                logger.error(f"刷新账号 [{account.username}] 失败: {e}")

        await db.commit()

    logger.info("账号刷新完成")


async def sync_download_status():
    """
    同步下载器中的种子状态到历史记录。
    将 downloading 状态更新为 seeding/completed 等。
    """
    from database import async_session
    from models import DownloadHistory, Downloader
    from services.downloader import create_downloader

    logger.info("开始同步下载状态")

    async with async_session() as db:
        # 获取所有活跃的下载记录（非终态）
        result = await db.execute(
            select(DownloadHistory).where(
                DownloadHistory.status.in_(["downloading", "seeding"])
            )
        )
        active_records = result.scalars().all()
        if not active_records:
            return

        # 按下载器分组
        dl_groups: dict[int, list] = {}
        for record in active_records:
            if record.downloader_id:
                dl_groups.setdefault(record.downloader_id, []).append(record)

        for dl_id, records in dl_groups.items():
            try:
                dl_result = await db.execute(select(Downloader).where(Downloader.id == dl_id))
                dl_model = dl_result.scalar_one_or_none()
                if not dl_model:
                    continue

                downloader = create_downloader(
                    dl_model.type, host=dl_model.host, port=dl_model.port,
                    username=dl_model.username, password=dl_model.password, use_ssl=dl_model.use_ssl,
                )

                # 获取下载器中所有种子状态
                all_torrents = await downloader.get_all_torrents()
                hash_map = {t.info_hash.lower(): t for t in all_torrents}

                for record in records:
                    if not record.info_hash:
                        continue
                    torrent_status = hash_map.get(record.info_hash.lower())
                    if torrent_status:
                        new_status = torrent_status.state  # downloading/seeding/completed/paused
                        if new_status != record.status:
                            old = record.status
                            record.status = new_status
                            logger.debug(f"种子 {record.torrent_id} 状态: {old} -> {new_status}")
                    else:
                        # 下载器中找不到，标记为已删除
                        if record.status != "deleted":
                            record.status = "deleted"
                            logger.info(f"种子 {record.torrent_id} 在下载器中不存在，标记为已删除")

            except Exception as e:
                logger.error(f"同步下载器 {dl_id} 状态失败: {e}")

        await db.commit()

    logger.info("下载状态同步完成")


async def check_expired_torrents():
    """
    保底定时器：遍历所有活跃种子，检查促销是否过期。
    精确定时器可能因重启等原因遗漏，此任务作为兜底。
    根据 expired_action 设置决定删除还是暂停，H&R 种子强制暂停。
    """
    from database import async_session
    from models import DownloadHistory, Downloader, SystemSetting
    from services.downloader import create_downloader

    logger.info("开始保底检查促销过期种子")

    async with async_session() as db:
        # 读取到期动作设置
        setting_result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == "auto_delete")
        )
        setting = setting_result.scalar_one_or_none()
        config = setting.value if setting else {}

        # 主开关关闭时：不做任何到期保护动作（暂停/删除都不执行）
        # 重要警示：关闭后可能错过免费到期时间点，带来账号风险，请在 README 中特别标注。
        if not config.get("enabled") or not config.get("delete_expired"):
            logger.warning("保底过期检查：到期保护已关闭，跳过处理")
            return

        expired_action = config.get("expired_action", "delete")

        now = datetime.utcnow()
        result = await db.execute(
            select(DownloadHistory).where(
                DownloadHistory.discount_end_time != None,
                DownloadHistory.discount_end_time < now,
                DownloadHistory.status.in_(["downloading", "seeding"]),
            )
        )
        expired = result.scalars().all()

        for record in expired:
            try:
                # H&R 种子强制暂停
                action = "pause" if record.has_hr else expired_action

                if record.has_hr:
                    logger.warning(f"种子 [{record.torrent_id}] {record.title[:40]} 是 H&R 种子，强制暂停")

                if not record.downloader_id or not record.info_hash:
                    record.status = "expired_paused" if action == "pause" else "expired_deleted"
                    continue

                dl_result = await db.execute(
                    select(Downloader).where(Downloader.id == record.downloader_id)
                )
                dl_model = dl_result.scalar_one_or_none()
                if not dl_model:
                    continue

                downloader = create_downloader(
                    dl_model.type, host=dl_model.host, port=dl_model.port,
                    username=dl_model.username, password=dl_model.password, use_ssl=dl_model.use_ssl,
                )

                if action == "pause":
                    await downloader.pause_torrent(record.info_hash)
                    record.status = "expired_paused"
                    logger.info(f"保底-促销到期暂停: [{record.torrent_id}] {record.title[:40]}")
                else:
                    await downloader.remove_torrent(record.info_hash, delete_files=True)
                    record.status = "expired_deleted"
                    logger.info(f"保底-促销到期删种: [{record.torrent_id}] {record.title[:40]}")

            except Exception as e:
                logger.error(f"保底处理过期种子 {record.torrent_id} 失败: {e}")

        await db.commit()

    logger.info("保底促销过期检查完成")

    # 顺带检查下载中的非免费种子
    await check_non_free_downloading()


async def check_non_free_downloading():
    """
    删除下载中的非免费种子：
    遍历所有 status=downloading 的记录，如果 discount_type 为空（非免费），则删除。
    H&R 种子跳过。
    """
    from database import async_session
    from models import DownloadHistory, Downloader, SystemSetting
    from services.downloader import create_downloader

    logger.info("开始检查下载中的非免费种子")

    async with async_session() as db:
        # 读取自动删种设置
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == "auto_delete")
        )
        setting = result.scalar_one_or_none()
        if not setting or not setting.value:
            return
        config = setting.value
        if not config.get("enabled") or not config.get("delete_non_free"):
            return

        # 获取所有下载中的记录
        hist_result = await db.execute(
            select(DownloadHistory).where(DownloadHistory.status == "downloading")
        )
        records = hist_result.scalars().all()

        for record in records:
            try:
                # 有促销类型的跳过（免费、2x 等）
                if record.discount_type:
                    continue

                # H&R 种子跳过
                if record.has_hr:
                    logger.debug(f"种子 [{record.torrent_id}] 是 H&R 种子，跳过非免费删除")
                    continue

                if not record.downloader_id or not record.info_hash:
                    record.status = "deleted"
                    continue

                dl_result = await db.execute(
                    select(Downloader).where(Downloader.id == record.downloader_id)
                )
                dl_model = dl_result.scalar_one_or_none()
                if not dl_model:
                    continue

                downloader = create_downloader(
                    dl_model.type, host=dl_model.host, port=dl_model.port,
                    username=dl_model.username, password=dl_model.password, use_ssl=dl_model.use_ssl,
                )
                await downloader.remove_torrent(record.info_hash, delete_files=True)
                record.status = "deleted"
                logger.info(f"非免费删种: [{record.torrent_id}] {record.title[:40]}")

            except Exception as e:
                logger.error(f"删除非免费种子 {record.torrent_id} 失败: {e}")

        await db.commit()

    logger.info("非免费种子检查完成")


async def check_dynamic_delete():
    """
    动态容量删种：当下载器已用空间超过上限阈值时，
    按创建时间从早到晚删除做种中的种子，直到已用空间降至目标值。
    """
    from database import async_session
    from models import DownloadHistory, Downloader, SystemSetting
    from services.downloader import create_downloader

    logger.info("开始检查动态容量删种")

    async with async_session() as db:
        # 读取自动删种设置
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == "auto_delete")
        )
        setting = result.scalar_one_or_none()
        if not setting or not setting.value:
            return
        config = setting.value
        if not config.get("enabled"):
            return
        if not config.get("dynamic_delete_enabled"):
            return

        # 兼容旧字段 disk_threshold_gb
        disk_max_gb = config.get("disk_max_gb") or config.get("disk_threshold_gb", 10000)
        disk_target_gb = config.get("disk_target_gb", disk_max_gb * 0.8)
        max_bytes = disk_max_gb * (1024 ** 3)
        target_bytes = disk_target_gb * (1024 ** 3)

        # 遍历所有下载器检查磁盘空间
        dl_result = await db.execute(select(Downloader))
        for dl_model in dl_result.scalars().all():
            try:
                downloader = create_downloader(
                    dl_model.type, host=dl_model.host, port=dl_model.port,
                    username=dl_model.username, password=dl_model.password, use_ssl=dl_model.use_ssl,
                )
                stats = await downloader.get_stats()
                used_bytes = stats.total_size - stats.free_space

                if used_bytes < max_bytes:
                    continue

                logger.warning(
                    f"下载器 [{dl_model.name}] 已用空间 {used_bytes / (1024**3):.1f}GB "
                    f">= 上限 {disk_max_gb}GB，开始动态删种，目标降至 {disk_target_gb}GB"
                )

                # 获取该下载器上做种中的历史记录，按创建时间升序（先删旧的）
                hist_result = await db.execute(
                    select(DownloadHistory).where(
                        DownloadHistory.downloader_id == dl_model.id,
                        DownloadHistory.status == "seeding",
                    ).order_by(DownloadHistory.created_at.asc())
                )
                candidates = hist_result.scalars().all()

                freed = 0
                for record in candidates:
                    if used_bytes - freed <= target_bytes:
                        break
                    # H&R 种子绝不能因容量不足而删除
                    if record.has_hr:
                        logger.warning(f"种子 [{record.torrent_id}] 是 H&R 种子，跳过动态删种")
                        continue
                    try:
                        if record.info_hash:
                            await downloader.remove_torrent(record.info_hash, delete_files=True)
                        record.status = "dynamic_deleted"
                        freed += record.size
                        logger.info(f"动态删种: [{record.torrent_id}] {record.title[:40]}")
                    except Exception as e:
                        logger.error(f"动态删种失败 {record.torrent_id}: {e}")

                await db.commit()

            except Exception as e:
                logger.error(f"检查下载器 [{dl_model.name}] 磁盘空间失败: {e}")

    logger.info("动态容量删种检查完成")


async def check_unregistered_torrents():
    """
    检查下载器中 tracker 状态为 unregistered 的种子，自动删除。
    通过下载器 API 获取种子的 tracker 状态来判断。
    """
    from database import async_session
    from models import DownloadHistory, Downloader, SystemSetting
    from services.downloader import create_downloader

    logger.info("开始检查 unregistered 种子")

    async with async_session() as db:
        # 读取自动删种设置
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == "auto_delete")
        )
        setting = result.scalar_one_or_none()
        if not setting or not setting.value:
            return
        config = setting.value
        if not config.get("enabled"):
            return
        if not config.get("delete_unregistered"):
            return

        # 获取所有活跃记录
        hist_result = await db.execute(
            select(DownloadHistory).where(
                DownloadHistory.status.in_(["downloading", "seeding"])
            )
        )
        active_records = hist_result.scalars().all()
        if not active_records:
            return

        # 按下载器分组
        dl_groups: dict[int, list] = {}
        for record in active_records:
            if record.downloader_id and record.info_hash:
                dl_groups.setdefault(record.downloader_id, []).append(record)

        for dl_id, records in dl_groups.items():
            try:
                dl_result = await db.execute(select(Downloader).where(Downloader.id == dl_id))
                dl_model = dl_result.scalar_one_or_none()
                if not dl_model:
                    continue

                downloader = create_downloader(
                    dl_model.type, host=dl_model.host, port=dl_model.port,
                    username=dl_model.username, password=dl_model.password, use_ssl=dl_model.use_ssl,
                )

                # 获取所有种子状态
                all_torrents = await downloader.get_all_torrents()
                hash_map = {t.info_hash.lower(): t for t in all_torrents}

                for record in records:
                    torrent_status = hash_map.get(record.info_hash.lower())
                    if not torrent_status:
                        continue
                    # 检查 tracker 消息是否包含 unregistered
                    tracker_msg = getattr(torrent_status, "tracker_msg", "") or ""
                    if "unregistered" in tracker_msg.lower():
                        try:
                            await downloader.remove_torrent(record.info_hash, delete_files=True)
                            record.status = "unregistered_deleted"
                            logger.info(f"Unregistered 删种: [{record.torrent_id}] {record.title[:40]}")
                        except Exception as e:
                            logger.error(f"删除 unregistered 种子失败 {record.torrent_id}: {e}")

            except Exception as e:
                logger.error(f"检查下载器 {dl_id} unregistered 失败: {e}")

        await db.commit()

    logger.info("Unregistered 检查完成")


async def collect_stats_snapshot():
    """
    定时采集统计快照，用于仪表盘趋势图。
    记录每个账号的累计上传量，以及所有下载器的总上传速率。
    """
    from database import async_session
    from models import Account, Downloader, StatsSnapshot
    from services.downloader import create_downloader

    logger.info("开始采集统计快照")

    async with async_session() as db:
        # 获取所有账号的上传/下载量
        acc_result = await db.execute(select(Account).where(Account.is_active == True))
        accounts = acc_result.scalars().all()

        # 获取所有下载器的速率
        total_upload_speed = 0.0
        total_download_speed = 0.0
        dl_result = await db.execute(select(Downloader))
        for dl_model in dl_result.scalars().all():
            try:
                dl = create_downloader(
                    dl_model.type, host=dl_model.host, port=dl_model.port,
                    username=dl_model.username, password=dl_model.password, use_ssl=dl_model.use_ssl,
                )
                stats = await dl.get_stats()
                total_upload_speed += stats.upload_speed or 0
                total_download_speed += stats.download_speed or 0
            except Exception:
                pass

        # 为每个账号写入快照
        for acc in accounts:
            snapshot = StatsSnapshot(
                account_id=acc.id,
                uploaded=acc.uploaded or 0,
                downloaded=acc.downloaded or 0,
                upload_speed=total_upload_speed,
                download_speed=total_download_speed,
            )
            db.add(snapshot)

        # 如果没有账号，也写一条汇总记录
        if not accounts:
            snapshot = StatsSnapshot(
                account_id=None,
                uploaded=0, downloaded=0,
                upload_speed=total_upload_speed,
                download_speed=total_download_speed,
            )
            db.add(snapshot)

        await db.commit()

    logger.info("统计快照采集完成")
