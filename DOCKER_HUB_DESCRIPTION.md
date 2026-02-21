# NicePT Helper - Docker Hub 描述

## 简介

NicePT Helper 是一个针对 NicePT（基于 NexusPHP）的 PT 自动化管理系统。提供种子搜索、规则自动下载、下载器管理、H&R 考核监控等功能。

## 核心功能

- **PT 账号管理** — Cookie 认证，自动刷新上传/下载/分享率/魔力值
- **种子搜索与下载** — 关键词、分类、促销类型筛选，实时展示做种/下载状态
- **规则引擎自动下载** — 按促销、大小、做种人数、关键词等条件自动下载
- **下载器集成** — 支持 qBittorrent / Transmission，连接测试、标签管理、磁盘监控
- **下载历史与生命周期管理** — 全生命周期管理，状态同步，从下载器导入
- **自动删种** — 促销到期保护、动态容量删种、Unregistered 检查
- **H&R 考核监控** — 同步站点 H&R 数据，状态监控，魔力消除
- **定时任务调度** — 自动下载、账号刷新、状态同步、过期检查、动态删种等
- **仪表盘与日志管理** — 系统统计、趋势图、下载器状态、日志查看

## 快速开始

### 最简单的方式

```bash
docker run -d \
  --name nicept-helper \
  -p 8000:8000 \
  -e SECRET_KEY=$(openssl rand -base64 32) \
  -v nicept-data:/app/backend \
  spellyaohui/nicept-helper:latest
```

访问 `http://localhost:8000` 进行初始化。

### 使用 Docker Compose

```yaml
version: '3.8'

services:
  nicept-helper:
    image: spellyaohui/nicept-helper:latest
    container_name: nicept-helper
    ports:
      - "8000:8000"
    environment:
      - SECRET_KEY=your-random-secret-key-change-me
      - SITE_URL=https://www.nicept.net
      - REQUEST_DELAY=2.0
    volumes:
      - nicept-data:/app/backend
    restart: unless-stopped

volumes:
  nicept-data:
```

启动：

```bash
docker-compose up -d
```

## 环境变量

| 变量 | 说明 | 默认值 | 必需 |
|---|---|---|---|
| `SECRET_KEY` | JWT 密钥 | 无 | ✅ |
| `DATABASE_URL` | 数据库连接 | `sqlite+aiosqlite:///./nicept.db` | ❌ |
| `SITE_URL` | NicePT 站点地址 | `https://www.nicept.net` | ❌ |
| `REQUEST_DELAY` | 请求间隔（秒） | `2.0` | ❌ |

## 数据持久化

容器内数据存储在 `/app/backend`，包括：
- `nicept.db` - SQLite 数据库
- `logs/` - 应用日志

使用数据卷映射确保数据持久化：

```bash
-v nicept-data:/app/backend
```

## 技术栈

- **后端**：Python 3.12, FastAPI, SQLAlchemy 2.0, APScheduler
- **前端**：React 18, TypeScript, Vite 6, Tailwind CSS 4
- **数据库**：SQLite（默认）/ PostgreSQL
- **解析**：BeautifulSoup4 + lxml

## 镜像信息

- **大小**：~563MB
- **基础镜像**：Python 3.12-slim + Node.js 20-slim（多阶段构建）
- **标签**：`latest`（最新版本）、`v0.1.0`（特定版本）

## 首次启动

容器首次启动时会自动：
1. 初始化 SQLite 数据库
2. 创建数据表
3. 生成日志目录

首次访问时进入注册页面，创建管理员账号。

## 常见问题

### 如何修改 SECRET_KEY？

修改环境变量后重启容器：

```bash
docker-compose down
# 编辑 docker-compose.yml 中的 SECRET_KEY
docker-compose up -d
```

### 如何查看日志？

```bash
docker logs -f nicept-helper
```

### 如何备份数据库？

```bash
docker run --rm -v nicept-data:/data -v $(pwd):/backup \
  alpine cp /data/nicept.db /backup/nicept.db.backup
```

### 如何升级镜像？

```bash
docker pull spellyaohui/nicept-helper:latest
docker-compose down
docker-compose up -d
```

## 安全性

- 敏感文件（`.env`、数据库、缓存）不包含在镜像中
- 数据通过数据卷映射实现持久化
- 容器删除后数据不丢失
- 支持环境变量和配置文件两种配置方式

## 生产部署建议

1. **使用反向代理**（Nginx/Caddy）处理 HTTPS
2. **资源限制**：CPU 1 核，内存 1GB
3. **日志管理**：配置日志驱动防止日志文件过大
4. **定期备份**：定期备份 SQLite 数据库
5. **监控告警**：配置健康检查和告警

## 许可证

仅供个人学习使用。

## 项目链接

- **GitHub**：https://github.com/spellyaohui/NicePT-Helper
- **完整文档**：https://github.com/spellyaohui/NicePT-Helper/blob/master/DOCKER.md

## 支持

如有问题，请在 GitHub 提交 Issue。
