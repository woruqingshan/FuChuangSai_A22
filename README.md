# A22 本地开发骨架

## 1. 项目目标
本项目面向 A22 情感陪护虚拟数字人系统。

当前阶段的目标不是先接入真实推理服务，而是先完成本地非推理链路的搭建与验证，包括：

- 前端展示界面
- 本地边缘后端
- 本地统一入口
- 与未来远程推理服务的接口预留

## 2. 当前系统架构
当前架构按三层划分：

1. Windows 层  
   用于开发入口和展示入口，包括 `VS Code / Cursor`、浏览器、`Docker Desktop`。

2. WSL2 Ubuntu 22.04 层  
   作为本地 Linux 开发与运行环境，承载项目源码、本地 `frontend`、本地 `edge-backend`、`nginx`、日志与缓存。

3. Remote Server 层  
   承载全部推理相关服务，包括 `LLM`、`RAG`、`TTS`、多模态融合、状态评估等。

当前约定是：**所有正式推理全部部署在远程服务器，本地 WSL 仅负责展示、业务处理、转发和接口预留。**

## 3. 技术栈
当前本地开发骨架使用如下技术栈：

- Windows 11 + WSL2
- Ubuntu 22.04
- Docker Desktop
- Docker Compose
- Nginx
- Node.js 20
- Vite
- Python 3.11
- FastAPI
- NVIDIA GPU through WSL2 + Docker Desktop

## 4. 本地 Compose 服务说明
当前本地 `docker compose` 管理以下服务：

- `frontend`  
  本地前端开发服务与页面渲染入口。

- `edge-backend`  
  本地边缘后端，负责会话管理、请求处理、转发预留和 mock 返回。

- `nginx`  
  本地统一入口，用于路由前端页面和 `/api` 请求。

- `gpu-tools`  
  可选 GPU 工具容器，仅用于验证本机 GPU 到容器的链路，不属于主业务容器。

## 5. 目录结构
```text
A22/
├─ compose.yaml
├─ compose.local.yaml
├─ README.md
├─ frontend/
├─ edge-backend/
├─ shared/
├─ infra/nginx/
├─ logs/
└─ data/
```

## 6. Docker 在 WSL 下的配置步骤
本项目采用 **Windows 侧 Docker Desktop + WSL2 Ubuntu 22.04** 的方式，不在 WSL 内额外安装独立的 Docker Engine。

### 6.1 Windows 侧准备
1. 安装并更新 `WSL2`
2. 安装 `Docker Desktop`
3. 安装支持 WSL 的 `NVIDIA` 显卡驱动

### 6.2 Docker Desktop 设置
在 `Docker Desktop` 中确认：

- `Use WSL 2 based engine` 已开启
- `Resources > WSL Integration` 中已启用默认发行版
- `Ubuntu-22.04` 已勾选集成

### 6.3 WSL 内验证 Docker
进入 `Ubuntu-22.04` 后执行：

```bash
docker version
docker compose version
docker context ls
```

### 6.4 GPU 通路验证
当前环境已验证可用的测试镜像为：

```bash
docker run --rm --gpus all nvidia/cuda:12.6.3-base-ubuntu22.04 nvidia-smi
```

如果容器中可以正常显示本机显卡信息，说明 `WSL2 + Docker Desktop + GPU` 链路可用。

## 7. 首次拉起项目的操作步骤
如果是首次在当前机器拉起本项目，建议按下面步骤执行。

### 7.1 进入项目目录
```bash
cd ~/docker_ws/A22
```

### 7.2 拉取基础镜像
```bash
docker pull node:20-bookworm-slim
docker pull python:3.11-slim-bookworm
docker pull nginx:1.27-alpine
docker pull nvidia/cuda:12.6.3-base-ubuntu22.04
docker pull nvidia/cuda:12.6.3-cudnn-runtime-ubuntu22.04
```

### 7.3 启动本地服务
```bash
docker compose -f compose.yaml -f compose.local.yaml up -d
```

### 7.4 查看运行状态
```bash
docker compose -f compose.yaml -f compose.local.yaml ps
```

### 7.5 查看日志
```bash
docker compose -f compose.yaml -f compose.local.yaml logs -f
```

## 8. 已有 yml 情况下的复现步骤
如果仓库中已经存在 `compose.yaml` 和 `compose.local.yaml`，其他开发者复现本地环境时只需要完成以下操作。

### 8.1 前置条件
需要提前具备：

- Windows + WSL2
- Ubuntu 22.04
- Docker Desktop
- 已开启 WSL Integration

### 8.2 克隆仓库
```bash
git clone https://github.com/woruqingshan/A22_womenzhongjiangbaoyanGroup.git
cd A22_womenzhongjiangbaoyanGroup
```

如果你希望工作区仍位于 WSL 的 Linux 文件系统中，也可以先进入目标目录再克隆。

### 8.3 拉取依赖镜像
```bash
docker pull node:20-bookworm-slim
docker pull python:3.11-slim-bookworm
docker pull nginx:1.27-alpine
```

如果需要验证 GPU，再执行：

```bash
docker pull nvidia/cuda:12.6.3-base-ubuntu22.04
docker run --rm --gpus all nvidia/cuda:12.6.3-base-ubuntu22.04 nvidia-smi
```

### 8.4 启动服务
```bash
docker compose -f compose.yaml -f compose.local.yaml up -d
```

### 8.5 验证服务
```bash
docker compose -f compose.yaml -f compose.local.yaml ps
curl http://localhost:8000/health
curl -X POST http://localhost/api/chat -H "Content-Type: application/json" -d '{"text":"hello"}'
```

### 8.6 浏览器访问
推荐访问统一入口：

- `http://localhost`

补充说明：

- `http://localhost:3000` 是前端开发服务入口
- `http://localhost:8000` 是本地后端服务入口
- 当前完整链路推荐通过 `nginx` 的 `http://localhost` 来访问

## 9. 当前已完成内容
当前本地骨架已经完成以下验证：

- `frontend` 容器已启动
- `edge-backend` 容器已启动
- `nginx` 容器已启动
- `http://localhost:8000/health` 可访问
- `http://localhost/api/chat` 可访问
- `docker compose` 已可作为本地多服务管理入口

## 10. 下一步开发方向
下一阶段将基于当前骨架继续补齐以下功能：

- 前端渲染界面优化
- 前端输入信号接入
- 前后端本地闭环联调
- mock 远程 server 请求与返回
- 预留真实远程推理接口