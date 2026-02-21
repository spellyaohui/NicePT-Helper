# PT 复刻项目实施大纲（基于 M-Team Helper 研究）

## 1. 文档目标

本文档用于指导你基于现有 `M-Team Helper` 的思路，快速复刻一个同类型 PT 自动化系统。
目标是提供一份可直接落地的：

- 功能全景图
- API 设计清单
- 数据模型与模块边界
- 调度任务与业务时序
- 分阶段实施路线

---

## 2. 产品功能全景

### 2.1 核心功能模块

1. **认证与初始化**
   - 首次注册管理员
   - 登录/登出
   - Token 校验

2. **PT 账号管理**
   - 多账号维护
   - API Key 验证
   - 账号数据刷新（上传/下载/分享率/魔力）

3. **种子检索与详情**
   - 按关键字、分类、促销类型检索
   - 查看种子详情（简介、媒资信息、图片）
   - 获取下载链接与下载 `.torrent`

4. **自动下载规则引擎**
   - 普通规则 / 收藏监控规则
   - 条件：免费、2X、大小区间、做种人数、下载人数、关键词、分类、发布时间
   - 规则启停、排序、下载队列限制

5. **下载器管理**
   - 支持 qBittorrent / Transmission
   - 连接测试
   - 标签读取与创建
   - 统计信息（速度、磁盘空间、下载中/做种中数量）

6. **下载历史管理**
   - 历史分页、状态过滤
   - 手动上传种子到下载器
   - 从下载器导入历史
   - 历史删除与下载器联动删除

7. **自动删种体系**
   - 促销过期删种
   - 非免费删种
   - 动态容量阈值删种
   - Tracker unregistered 自动删种
   - 精准删种（到期前固定时间执行）

8. **调度与系统设置**
   - 刷新间隔配置
   - 时间段任务开关（自动下载/过期检查/账号刷新）
   - 调度器状态监控与重启

9. **仪表盘与日志中心**
   - 系统统计
   - 下载器状态面板
   - 最近活动
   - 日志读取/过滤/清理

---

## 3. 系统架构（推荐复刻）

### 3.1 分层架构

- **API 层（FastAPI Routers）**
  - 参数校验、权限校验、响应格式统一
- **业务层（Services）**
  - 站点抓取服务（PT Site Adapter）
  - 规则匹配服务（Rule Engine）
  - 下载器适配服务（Downloader Adapter）
  - 调度服务（Scheduler）
- **数据层（SQLAlchemy）**
  - 账号、规则、下载器、历史、系统设置
- **前端层（React）**
  - 仪表盘、账号、种子、规则、下载器、历史、设置

### 3.2 关键设计思想

- **站点适配解耦**：将站点 API 封装在单独适配器，后续替换为其他 PT 站只改这一层。
- **下载器适配解耦**：统一下载器接口，支持多实现（qB / TR / 未来扩展）。
- **规则与执行解耦**：规则只表达条件，不耦合抓取细节。
- **调度与接口解耦**：调度器只调用服务方法，接口仅用于手动触发与配置。

---

## 4. 数据模型（复刻建议）

### 4.1 必要数据表

1. **users**
   - 系统登录用户

2. **accounts**
   - PT 站账号（api_key、uid、统计字段）

3. **filter_rules**
   - 自动下载规则
   - 关键字段：
     - `rule_type`（normal/favorite）
     - `mode`（normal/adult）
     - `free_only`、`double_upload`
     - `min/max_size`
     - `min/max_seeders`
     - `min/max_leechers`
     - `keywords`、`exclude_keywords`
     - `categories`
     - `max_publish_hours`
     - `max_downloading`
     - `downloader_id`、`save_path`、`tags`
     - `sort_order`

4. **downloaders**
   - 下载器连接配置

5. **download_history**
   - 下载记录与生命周期状态
   - 关键字段：
     - `status`（downloading/seeding/completed/deleted/expired_deleted/dynamic_deleted...）
     - `info_hash`
     - `discount_type`、`discount_end_time`
     - `is_favorited`、`unfavorited_at`
     - `images`

6. **system_settings**
   - 自动删种、调度间隔、时间段控制等 JSON 设置

---

## 5. API 清单（按模块）

> 说明：以下为复刻时应保留的最小完整接口集合。

### 5.1 Auth

- `POST /auth/login`
- `POST /auth/register`
- `POST /auth/logout`
- `GET /auth/verify`
- `GET /auth/check-init`

### 5.2 Accounts

- `GET /accounts/`
- `POST /accounts/`
- `GET /accounts/{account_id}`
- `POST /accounts/{account_id}/refresh`
- `DELETE /accounts/{account_id}`

### 5.3 Rules

- `GET /rules/`
- `POST /rules/`
- `GET /rules/{rule_id}`
- `PUT /rules/{rule_id}`
- `DELETE /rules/{rule_id}`
- `POST /rules/{rule_id}/toggle`

### 5.4 Torrents

- `POST /torrents/search`
- `GET /torrents/categories`
- `GET /torrents/metadata`
- `GET /torrents/{torrent_id}`
- `POST /torrents/{torrent_id}/download`
- `GET /torrents/{torrent_id}/download-url`
- `POST /torrents/push`

### 5.5 Downloaders

- `GET /downloaders/`
- `POST /downloaders/`
- `POST /downloaders/test`
- `POST /downloaders/{downloader_id}/test`
- `DELETE /downloaders/{downloader_id}`
- `GET /downloaders/{downloader_id}/tags`
- `GET /downloaders/{downloader_id}/disk-space`
- `GET /downloaders/{downloader_id}/stats`
- `GET /downloaders/stats`

### 5.6 History

- `GET /history/`
- `GET /history/check-expired`
- `POST /history/upload-torrent`
- `GET /history/downloader-tags/{downloader_id}`
- `POST /history/sync-status`
- `POST /history/import-from-downloader`
- `GET /history/status-mapping`
- `DELETE /history/deleted`
- `DELETE /history/{history_id}`
- `DELETE /history/`

### 5.7 Settings

- `GET /settings/auto-delete`
- `PUT /settings/auto-delete`
- `GET /settings/refresh-intervals`
- `PUT /settings/refresh-intervals`
- `GET /settings/scheduler-status`
- `GET /settings/schedule-control`
- `PUT /settings/schedule-control`
- `POST /settings/restart-scheduler`
- `GET /settings/`
- `GET /settings/{key}`
- `PUT /settings/{key}`
- `DELETE /settings/{key}`

### 5.8 Dashboard / Logs / Health

- `GET /dashboard/`
- `GET /dashboard/accounts/{account_id}/stats`
- `GET /dashboard/downloader-stats`
- `GET /logs`
- `GET /logs/{filename}`
- `DELETE /logs/{filename}`
- `DELETE /logs?days=7`
- `GET /health`

---

## 6. 调度任务与执行时序

### 6.1 固定任务

1. `refresh_all_accounts`：刷新账号数据
2. `auto_download_torrents`：规则驱动自动下载
3. `monitor_favorite_torrents`：收藏转免费监控
4. `check_expired_torrents`：过期/非免费删种
5. `check_dynamic_delete`：动态容量删种
6. `check_unregistered_torrents`：删除站点已下架种子
7. `sync_download_status`：同步下载器实际状态

### 6.2 核心业务时序（自动下载）

1. 读取启用规则（按 `sort_order`）
2. 查询站点种子列表
3. 批量查询站点历史，跳过已下载种子
4. 执行规则匹配
5. 下载 `.torrent` 并推送下载器
6. 写入 `download_history`
7. 若有促销到期时间，注册精准删种任务

---

## 7. 复刻到“新 PT 站”时需要替换的点

### 7.1 必改（P0）

- 站点 API 认证方式（Token/Cookie）
- 种子检索接口与参数
- 种子详情字段结构
- 下载链接生成与 `.torrent` 下载方式
- 收藏相关接口（如有）

### 7.2 可能改动（P1）

- 促销类型映射（FREE、2X 等）
- 分类字段编码
- 时间字段格式（毫秒时间戳/ISO）
- 站点历史查询接口（若无则仅用本地历史去重）

### 7.3 可复用（P2）

- 下载器适配层
- 规则匹配框架
- 历史管理逻辑
- 调度与系统设置框架
- 前端页面结构

---

## 8. 分阶段实施计划（推荐）

### 阶段 1：最小闭环（1~3 天）

- 完成账号管理、种子搜索、推送下载器、历史记录
- 仅支持手动触发，不上自动调度

### 阶段 2：规则自动化（2~4 天）

- 完成规则 CRUD、`match_torrent`、自动下载任务
- 增加本地历史去重

### 阶段 3：安全与稳定（2~4 天）

- 增加状态同步、过期删种、日志管理
- 调整超时、重试、缓存策略

### 阶段 4：高级能力（3~6 天）

- 收藏监控规则
- 动态删种
- unregistered 检查
- 仪表盘完善

---

## 9. 复刻项目目录模板（建议）

```text
new-pt-helper/
  backend/
    main.py
    config.py
    database.py
    models.py
    routers/
      auth.py
      accounts.py
      torrents.py
      rules.py
      downloaders.py
      history.py
      settings.py
      dashboard.py
      logs.py
    services/
      site_adapter.py
      downloader.py
      scheduler.py
      rule_engine.py
    utils/
  frontend/
    src/
      api/
      pages/
      components/
```

---

## 10. 风险与注意事项

1. **站点风控风险**：请求频率过高可能触发风控，需限速与重试退避。
2. **删种安全风险**：必须保证“只删下载中/符合范围/标签匹配”的保护逻辑。
3. **状态一致性风险**：下载器状态与数据库可能短时不一致，依赖定时同步修正。
4. **接口变更风险**：站点 API 结构变化时，优先改适配器层，避免扩散。

---

## 11. 结论

你要复刻同类 PT 项目时，建议优先复用：

- **规则引擎结构**
- **调度任务框架**
- **下载器适配层**
- **历史状态机设计**

并将“站点差异”集中在 `site_adapter` 中处理。这样后续支持第 2、3 个 PT 站时，系统可以快速扩展。
