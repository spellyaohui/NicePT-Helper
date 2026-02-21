# Docker 部署指南

NicePT Helper 已发布到 Docker Hub，支持一键部署。

## 镜像信息

- **镜像名称**：`spellyaohui/nicept-helper`
- **标签**：`latest`（最新版本）、`v0.1.0`（特定版本）
- **镜像大小**：~563MB
- **基础镜像**：Python 3.12-slim + Node.js 20-slim（多阶段构建）

## 快速开始

### 方式一：Docker 命令行

```bash
# 拉取镜像
docker pull spellyaohui/nicept-helper:latest

# 运行容器
docker run -d \
  --name nicept-helper \
  -p 8000:8000 \
  -e SECRET_KEY=your-random-secret-key \
  -e SITE_URL=https://www.nicept.net \
  -e REQUEST_DELAY=2.0 \
  -v nicept-data:/app/backend \
  spellyaohui/nicept-helper:latest
```

### 方式二：Docker Compose（推荐）

创建 `docker-compose.yml`：

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
      - DATABASE_URL=sqlite+aiosqlite:///./nicept.db
      - SITE_URL=https://www.nicept.net
      - REQUEST_DELAY=2.0
    volumes:
      - nicept-data:/app/backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8000/api/health', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s

volumes:
  nicept-data:
    driver: local
```

启动：

```bash
docker-compose up -d
```

## 环境变量配置

### 必需变量

| 变量名 | 说明 | 默认值 | 示例 |
|---|---|---|---|
| `SECRET_KEY` | JWT 密钥，务必修改 | 无 | `your-random-secret-key` |

### 可选变量

| 变量名 | 说明 | 默认值 | 示例 |
|---|---|---|---|
| `DATABASE_URL` | 数据库连接字符串 | `sqlite+aiosqlite:///./nicept.db` | `sqlite+aiosqlite:///./nicept.db` |
| `SITE_URL` | NicePT 站点地址 | `https://www.nicept.net` | `https://www.nicept.net` |
| `REQUEST_DELAY` | 请求间隔（秒），防风控 | `2.0` | `2.0` |

### 生成安全的 SECRET_KEY

```bash
# Linux/Mac
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Windows PowerShell
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 或使用 OpenSSL
openssl rand -base64 32
```

## 数据持久化

### 数据卷映射

容器内数据存储在 `/app/backend`，包括：
- `nicept.db` - SQLite 数据库
- `logs/` - 应用日志

**推荐使用 Docker 命名卷**（自动管理）：

```bash
docker run -d \
  -v nicept-data:/app/backend \
  spellyaohui/nicept-helper:latest
```

**或使用本地目录映射**（便于备份）：

```bash
# 创建本地数据目录
mkdir -p ./nicept-data

# 运行容器
docker run -d \
  -v $(pwd)/nicept-data:/app/backend \
  spellyaohui/nicept-helper:latest
```

### 备份数据库

```bash
# 使用命名卷
docker run --rm -v nicept-data:/data -v $(pwd):/backup \
  alpine cp /data/nicept.db /backup/nicept.db.backup

# 使用本地目录
cp ./nicept-data/nicept.db ./nicept.db.backup
```

### 恢复数据库

```bash
# 停止容器
docker-compose down

# 恢复备份
cp ./nicept.db.backup ./nicept-data/nicept.db

# 重启容器
docker-compose up -d
```

## 环境变量配置方式对比

### 方式一：环境变量（推荐用于简单配置）

**优点**：
- 简单直观
- 适合容器编排（Kubernetes、Swarm）
- 敏感信息可通过 secrets 管理

**缺点**：
- 不适合大量配置
- 容器重启后需重新设置

**使用方式**：

```bash
docker run -d \
  -e SECRET_KEY=your-key \
  -e SITE_URL=https://www.nicept.net \
  spellyaohui/nicept-helper:latest
```

### 方式二：配置文件映射（推荐用于复杂配置）

创建 `.env` 文件：

```env
SECRET_KEY=your-random-secret-key
DATABASE_URL=sqlite+aiosqlite:///./nicept.db
SITE_URL=https://www.nicept.net
REQUEST_DELAY=2.0
```

运行容器：

```bash
docker run -d \
  --env-file .env \
  -v nicept-data:/app/backend \
  spellyaohui/nicept-helper:latest
```

或在 docker-compose.yml 中：

```yaml
services:
  nicept-helper:
    image: spellyaohui/nicept-helper:latest
    env_file: .env
    volumes:
      - nicept-data:/app/backend
```

## 首次启动

容器首次启动时会自动：
1. 初始化 SQLite 数据库
2. 创建数据表
3. 生成日志目录

**首次访问**：

```
http://localhost:8000
```

进入注册页面，创建管理员账号。

## 日志查看

```bash
# 查看实时日志
docker logs -f nicept-helper

# 查看最后 100 行日志
docker logs --tail 100 nicept-helper

# 查看容器内日志文件
docker exec nicept-helper ls -la /app/backend/logs/
```

## 常见问题

### Q: 如何修改 SECRET_KEY？

A: 修改环境变量后重启容器：

```bash
docker-compose down
# 编辑 docker-compose.yml 中的 SECRET_KEY
docker-compose up -d
```

### Q: 数据库损坏了怎么办？

A: 删除数据卷，容器重启时会重新初始化：

```bash
docker-compose down
docker volume rm nicept-data
docker-compose up -d
```

### Q: 如何升级镜像版本？

A: 拉取新版本并重启：

```bash
docker pull spellyaohui/nicept-helper:latest
docker-compose down
docker-compose up -d
```

### Q: 容器无法启动？

A: 检查日志：

```bash
docker logs nicept-helper
```

常见原因：
- `SECRET_KEY` 未设置
- 端口 8000 被占用
- 数据卷权限问题

### Q: 如何在容器内执行命令？

A: 使用 `docker exec`：

```bash
# 进入容器 shell
docker exec -it nicept-helper /bin/bash

# 查看数据库
docker exec nicept-helper sqlite3 /app/backend/nicept.db ".tables"
```

## 镜像安全性

### 敏感文件排除

Dockerfile 和 .dockerignore 确保以下文件**不会**被打包进镜像：

- `.env` - 环境变量配置
- `*.db` - 数据库文件
- `__pycache__/` - Python 缓存
- `node_modules/` - Node 依赖
- `.git/` - Git 历史
- `.kiro/` - IDE 配置

### 数据隔离

- 数据库和日志存储在 `/app/backend`
- 通过数据卷映射实现持久化
- 容器删除后数据不丢失

## 生产部署建议

### 1. 使用反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. 使用 HTTPS

```bash
# 使用 Let's Encrypt 证书
docker run -d \
  -p 443:443 \
  -v /etc/letsencrypt:/etc/letsencrypt \
  -v nicept-data:/app/backend \
  spellyaohui/nicept-helper:latest
```

### 3. 资源限制

```yaml
services:
  nicept-helper:
    image: spellyaohui/nicept-helper:latest
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### 4. 日志管理

```yaml
services:
  nicept-helper:
    image: spellyaohui/nicept-helper:latest
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 多容器编排（Kubernetes）

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nicept-helper
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nicept-helper
  template:
    metadata:
      labels:
        app: nicept-helper
    spec:
      containers:
      - name: nicept-helper
        image: spellyaohui/nicept-helper:latest
        ports:
        - containerPort: 8000
        env:
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: nicept-secrets
              key: secret-key
        - name: SITE_URL
          value: "https://www.nicept.net"
        volumeMounts:
        - name: data
          mountPath: /app/backend
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: nicept-pvc
```

## 许可证

仅供个人学习使用。
