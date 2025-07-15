# 多模型智能报告与对话平台 v2.0

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-專業架構-green)
![React](https://img.shields.io/badge/React-狀態提升-blue)
![LangChain](https://img.shields.io/badge/LangChain-賦能-orange)

允许用户选择不同的云端或本地大语言模型（LLM）进行交互。项目支持两种核心模式：用于快速问答的**流式对话模式**，以及用于深度分析、可并行调用多个模型生成多份报告的**混合报告模式**。



---

## ✨ 核心功能

- **统一对话界面**: 以聊天为核心交互方式，整合所有功能。
- **多模型支持与切换**: 通过下拉菜单轻松切换不同的LLM（如Gemini, DeepSeek, 本地vLLM模型）。
- **流式对话模式**: 与单个模型进行实时、带上下文的连续对话，响应以打字机效果呈现。
- **混合报告模式**: 并行调用多个预设模型，一次性生成多份结构化报告，并在对话流中以内嵌标签页的形式进行展示和比较。
- **智能检索推荐**: 在用户输入新主题时，通过向量相似度搜索，主动推荐相关的历史报告。
- **持久化存储与历史追溯**: 所有采纳的报告方案和对话历史（未来可扩展）都可被保存，并通过专门的历史页面进行检索和回顾。
- **文件下载**: 支持将任何生成的报告或历史报告下载为 `.md` 文件。

## 🏛️ 项目架构

项目采用前后端分离的架构

**后端 (`backend/`) 目录结构:**
```
backend/
├── api/
│   └── routes.py         # API层：定义所有HTTP端点，处理请求和响应。
├── config/               # 配置层：管理所有配置，如API密钥、模型映射等。
│   └── config.py
├── database/
│   ├── connection.py     # 数据库连接会话。
│   └── models.py         # 数据表ORM模型定义。
├── prompts/
│   └── report_prompts.py # Prompt层：存放所有提示词模板。
├── services/
│   ├── model_adapters.py # 服务层：模型适配器，统一不同LLM的调用接口。
│   └── report_generator.py # 服务层：封装核心业务逻辑，如生成报告、处理对话流。
├── schemas/
│   └── report_schemas.py # Schema层：定义数据结构和验证规则 (Pydantic)。
├── main.py               # 应用主入口：组装App，加载中间件和路由。
└── .env                  # 环境变量文件，存储敏感密钥。
```
**注意**: 我已根据您的说明，将原 `core` 文件夹命名为 `config`。

## 🛠️ 技术栈

- **后端**: Python, FastAPI, Uvicorn, LangChain, `pydantic-settings`
- **前端**: React (Vite), JavaScript, `react-router-dom`, `axios`
- **数据库**:
  - **元数据存储**: SQLAlchemy + SQLite
  - **向量存储**: ChromaDB
- **AI & ML**:
  - **LLM集成**: `langchain-google-genai`, `langchain-openai`
  - **向量嵌入**: `sentence-transformers`

## 🚀 开发环境启动

### 1. 准备工作
- 确保已安装 Git, Node.js (v18+), 和 Conda。
- 克隆本项目到本地。

### 2. 后端设置
```bash
# 进入后端目录
cd backend

# 创建并激活 Conda 环境
conda create --name report_gen python=3.11 -y
conda activate report_gen

# 安装Python依赖
pip install -r requirements.txt

# 创建 .env 文件并填入您的API密钥
# (可以复制 .env.example 并重命名)
cp .env.example .env 
```
编辑 `.env` 文件，填入所有必需的API密钥和URL。

### 3. 前端设置
```bash
# 进入前端目录
cd frontend

# 安装Node.js依赖
npm install
```

### 4. 启动服务

**推荐方式 (一键启动):**
```bash
# 在 frontend 目录下运行
npm run start:all
```

**手动分别启动:**
- **启动后端**: 在项目**根目录**下运行 `uvicorn backend.main:app --reload`
- **启动前端**: 在 `frontend` 目录下运行 `npm run dev`

项目启动后，请在浏览器中访问 **`http://localhost:5173`**。

## 📦 生产环境部署 (概念指南)

将本项目部署到生产服务器通常包含以下步骤：

### 1. 前端打包
在 `frontend` 目录下运行打包命令：
```bash
npm run build
```
这会在 `frontend/dist` 目录下生成一套优化过的、纯静态的HTML, CSS, JS文件。

### 2. 后端部署
不应再使用 `uvicorn --reload`。推荐使用 `Gunicorn` + `Uvicorn worker` 的组合来运行FastAPI应用。
```bash
# 在 backend 目录下运行
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.main:app
```
* `-w 4`: 启动4个工作进程。
* `-k uvicorn.workers.UvicornWorker`: 使用Uvicorn作为工作进程的类型，以支持ASGI。

### 3. 使用Nginx作为反向代理
在生产环境中，通常使用Nginx作为web服务器和反向代理，来接收所有外部请求。

**Nginx配置示例**:
```nginx
server {
    listen 80;
    server_name your_domain.com;

    # 根路径指向前端打包后的文件
    location / {
        root /path/to/your/project/frontend/dist;
        try_files $uri /index.html;
    }

    # 所有 /api 的请求都转发给后端FastAPI服务
    location /api/ {
        proxy_pass [http://127.0.0.1:8000](http://127.0.0.1:8000);
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```
### 4. 进程管理
使用 `systemd` (Linux) 或 `Docker` 来管理Gunicorn进程，确保服务在后台稳定运行并在意外退出后能自动重启。

---

## 📄 License

本项目采用 [MIT License](LICENSE) 授权。