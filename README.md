# NicePT Helper

NicePT Helper 是一个针对 NicePT（基于 NexusPHP）的 PT 自动化管理系统，提供种子搜索、规则自动下载、下载器管理、H&R 考核监控等功能。

## 功能概览

- **账号管理** — Cookie 认证，自动刷新上传/下载/分享率/魔力值
- **种子搜索** — 关键词、分类、促销类型筛选，实时展示做种/下载状态
- **规则引擎** — 按促销、大小、做种人数、关键词等条件自动下载
- **下载器集成** — 支持 qBittorrent / Transmission，连接测试、标签管理、磁盘监控
- **下载历史** — 全生命周期管理，状态同步，从下载器导入
- **自动删种** — 促销到期保护（暂停/删除）、动态容量删种、Unregistered（失效种子）检查
- **H&R 考核** — 同步站点 H&R 数据，状态监控，魔力消除
- **定时任务** — interval 调度（自动下载、账号刷新、状态同步、过期检查、动态删种、失效种子检查、统计快照）+ **每个种子独立到期定时器**（避免错过免费到期）
- **仪表盘** — 系统统计、趋势图、下载器状态
- **日志管理** — 查看、筛选、清理

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.10+, FastAPI, SQLAlchemy 2.0 (async), APScheduler |
| 前端 | React 18, TypeScript, Vite 6, Tailwind CSS 4 |
| 数据库 | SQLite (默认) / PostgreSQL |
| HTTP | httpx (异步), Axios |
| 解析 | BeautifulSoup4 + lxml |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- npm 或 yarn

### 1. 克隆项目

```bash
git clone https://github.com/spellyaohui/NicePT-Helper.git
cd NicePT-Helper
```

### 2. 后端

```bash
# 安装依赖
pip install -r backend/requirements.txt

# 配置环境变量
cp backend/.env.example backend/.env
# 编辑 .env，填写 SECRET_KEY 和站点信息
```

`.env` 关键配置项：

```env
SECRET_KEY=your-random-secret-key    # JWT 密钥，务必修改
DATABASE_URL=sqlite+aiosqlite:///./nicept.db
SITE_URL=https://www.nicept.net      # NicePT 站点地址
REQUEST_DELAY=2.0                    # 请求间隔（秒），防风控
```

```bash
# 启动后端（端口 8000）
python backend/main.py
```

首次启动会自动创建数据库表。

### 3. 前端

```bash
cd frontend
npm install
npm run dev    # 开发模式，端口 3000
```

打开 `http://localhost:3000`，首次访问会进入注册页面创建管理员账号。

### 4. 生产构建

```bash
cd frontend
npm run build    # 输出到 frontend/dist/
```

生产环境可用 Nginx 托管前端静态文件，反向代理 `/api` 到后端。

## 部署方案

### 方案一：直接部署

适合个人使用，最简单的方式：

```bash
# 后端（后台运行）
nohup python backend/main.py > backend/logs/app.log 2>&1 &

# 前端构建后用 Nginx 托管
npm run build --prefix frontend
```

Nginx 参考配置：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 方案二：Docker 部署（推荐）

```dockerfile
# Dockerfile 示例
FROM python:3.12-slim
WORKDIR /app
COPY backend/ ./backend/
COPY frontend/dist/ ./frontend/dist/
RUN pip install --no-cache-dir -r backend/requirements.txt
EXPOSE 8000
CMD ["python", "backend/main.py"]
```

```bash
docker build -t nicept-helper .
docker run -d -p 8000:8000 -v ./data:/app/backend/nicept.db --env-file backend/.env nicept-helper
```

### 方案三：systemd 服务

```ini
# /etc/systemd/system/nicept-helper.service
[Unit]
Description=NicePT Helper
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/nicept-helper
ExecStart=/usr/bin/python3 backend/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable nicept-helper
sudo systemctl start nicept-helper
```

## 项目结构

```
NicePT-Helper/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理
│   ├── database.py          # 异步数据库
│   ├── models.py            # 数据模型
│   ├── routers/             # API 路由（auth, accounts, torrents, rules, downloaders, history, settings, dashboard, logs, hr, site_login）
│   ├── services/            # 业务逻辑（site_adapter, downloader, scheduler, rule_engine, login_service）
│   ├── utils/               # 工具（JWT 认证）
│   └── static/              # 静态文件
├── frontend/
│   └── src/
│       ├── pages/           # 10 个页面（仪表盘、账号、种子、规则、下载器、历史、H&R、设置、日志、登录）
│       ├── components/      # 全局布局
│       ├── contexts/        # 认证 & 主题
│       └── api/             # Axios 客户端
└── README.md
```

## 使用流程

1. 注册管理员账号并登录
2. 在「账号管理」添加 NicePT 账号（填入 Cookie）
3. 在「下载器」添加 qBittorrent 或 Transmission 连接
4. 在「种子搜索」手动搜索并下载，或在「自动规则」配置自动下载条件
5. 在「系统设置」配置并开启定时任务（自动下载、动态删种、失效种子检查等）
6. 在「系统设置 → 自动删种设置」开启“启用自动删种”和“删除促销到期的种子”（如需到期保护）
7. 在「H&R 考核」同步并监控 H&R 状态

## 注意事项

- NicePT 基于 NexusPHP，没有 REST API，所有数据通过 HTML 页面解析获取
- 请求间隔默认 2 秒，避免触发站点风控
- H&R 种子在考核未通过前不会被自动删除
- Cookie 过期后需要重新登录站点获取新 Cookie
- 建议定期备份 `nicept.db` 数据库文件

### 重要警示：关闭“自动删种主开关”的影响（请务必确认）

系统对“免费/促销到期”的处理采用了：
- **每个种子一个精确定时器**（date trigger，到期前触发）；
- 以及一个 **保底过期检查**（interval trigger，防止因异常漏掉）。

但如果你在「系统设置 → 自动删种设置」里关闭了：
- `enabled`（启用自动删种，主开关），或
- `delete_expired`（删除促销到期的种子/到期处理开关），

那么系统将**停止执行所有到期保护动作**（包括“精确到期暂停/删除”和“保底过期检查”）。

另外，当你在前端重新打开上述开关、或系统重启后，如果开关处于开启状态，系统会尝试**自动恢复所有下载中/做种中种子的精确到期定时器**，确保到期保护能够继续正常运作。

这意味着：
- 关闭开关期间，可能会错过免费到期的关键时间点；
- 若站点规则对非免费状态、做种策略等敏感，存在**账号信誉/安全风险**。

建议：除非你明确知道后果，否则不要关闭上述开关。

## 许可证

仅供个人学习使用。
