# 项目结构

## 目录布局

```
backend/
├── main.py                  # FastAPI 应用入口
├── config.py                # 配置管理（pydantic-settings）
├── database.py              # 异步数据库连接与会话
├── models.py                # SQLAlchemy 数据模型
├── requirements.txt         # Python 依赖
├── .env.example             # 环境变量模板
├── routers/                 # API 路由
│   ├── auth.py              # 认证（注册/登录/登出/验证/初始化检查）
│   ├── accounts.py          # PT 账号管理
│   ├── torrents.py          # 种子搜索、分类、元数据、下载
│   ├── rules.py             # 自动下载规则 CRUD + 启停
│   ├── downloaders.py       # 下载器管理（连接测试/标签/磁盘/统计）
│   ├── history.py           # 下载历史（分页/同步/导入/上传/清理）
│   ├── settings.py          # 系统设置（自动删种/调度/间隔）
│   ├── dashboard.py         # 仪表盘（汇总/账号统计/下载器状态）
│   ├── logs.py              # 日志管理（查看/删除/清理）
│   └── site_login.py        # NicePT 站点登录（Challenge-Response）
├── services/                # 业务逻辑层
│   ├── site_adapter.py      # NexusPHP 站点适配器（HTML 爬虫）
│   ├── login_service.py     # NicePT 登录服务（验证码+挑战响应）
│   ├── downloader.py        # 下载器适配器（qB/Transmission）
│   ├── scheduler.py         # APScheduler 调度服务（7 种定时任务）
│   └── rule_engine.py       # 规则匹配引擎
├── utils/
│   └── auth.py              # JWT 认证工具
├── static/
│   └── login_test.html      # 登录测试页面
└── logs/                    # 日志文件目录
```

## 数据模型

- users: 系统用户
- accounts: PT 站账号（Cookie + Passkey 认证）
- filter_rules: 自动下载规则
- downloaders: 下载器连接配置
- download_history: 下载记录与生命周期状态
- system_settings: 键值对系统设置

## 关键模块说明

### site_adapter.py（核心）
NexusPHP 站点没有 REST API，通过 HTML 页面解析实现：
- 使用 Cookie 认证，不是 API Key
- 使用 BeautifulSoup + lxml 解析页面
- 内置请求限速防风控
- 需要根据 NicePT 实际页面结构调整解析器

### downloader.py
统一接口，工厂模式创建实例：
- QBittorrentAdapter: qBittorrent Web API v2
- TransmissionAdapter: Transmission RPC

### scheduler.py
7 种定时任务：自动下载、账号刷新、状态同步、过期检查、动态删种、unregistered 检查

### 所有 API 路由前缀为 /api

## 前端结构

```
frontend/
├── index.html               # 入口 HTML
├── vite.config.ts            # Vite 配置（代理、别名、Tailwind 插件）
├── package.json
├── tsconfig.json
└── src/
    ├── main.tsx              # React 入口
    ├── App.tsx               # 路由配置
    ├── index.css             # 全局样式（Tailwind）
    ├── api/
    │   └── client.ts         # Axios 实例（baseURL、拦截器）
    ├── components/
    │   └── Layout.tsx        # 全局布局（侧边栏 + 内容区）
    ├── contexts/
    │   ├── AuthContext.tsx    # JWT 认证状态管理
    │   └── ThemeContext.tsx   # 主题切换（亮/暗）
    └── pages/
        ├── LoginPage.tsx     # 登录页
        ├── DashboardPage.tsx # 仪表盘
        ├── AccountsPage.tsx  # 账号管理
        ├── TorrentsPage.tsx  # 种子搜索
        ├── RulesPage.tsx     # 规则管理
        ├── DownloadersPage.tsx # 下载器管理
        ├── HistoryPage.tsx   # 下载历史
        ├── SettingsPage.tsx  # 系统设置
        └── LogsPage.tsx      # 日志查看
```
