# 技术栈

## 后端

- Python 3.10+
- FastAPI + Uvicorn（异步 Web 框架）
- SQLAlchemy 2.0（异步 ORM）+ aiosqlite
- Pydantic v2（数据校验）
- httpx（异步 HTTP 客户端）
- BeautifulSoup4 + lxml（HTML 解析）
- APScheduler（定时任务）
- python-jose + passlib（JWT 认证）

## 前端

- React 18 + TypeScript
- Vite 6（构建工具）
- Tailwind CSS 4（样式）
- React Router 6（路由）
- Axios（HTTP 客户端）
- Lucide React（图标）

## 前端补充

- Recharts（图表库，用于仪表盘）
- 路径别名：`@` → `frontend/src`

## 常用命令

```bash
# 后端
pip install -r backend/requirements.txt
python backend/main.py            # 启动后端，端口 8000

# 前端
cd frontend && npm install
cd frontend && npm run dev         # 开发模式，端口 3000
cd frontend && npm run build       # 生产构建（先 tsc 再 vite build）
cd frontend && npm run preview     # 预览生产构建
```

## 关键技术决策

- NexusPHP 站点无 REST API，使用 HTML 爬虫方式
- Cookie + Passkey 认证（非 API Key）
- 异步全栈（async/await）
- SQLite 作为默认数据库（sqlite+aiosqlite），可切换 PostgreSQL
- 请求限速防风控（默认 2 秒间隔）
- 前端通过 Vite 代理 /api 到后端 http://127.0.0.1:8000
- CORS 全开放（开发阶段）
- 应用使用 FastAPI lifespan 管理启动/关闭（数据库初始化、调度器启停）
