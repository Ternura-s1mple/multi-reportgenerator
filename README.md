# 多模型报告生成与管理平台

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-green)
![React](https://img.shields.io/badge/React-18.2.0-blue)
![Vite](https://img.shields.io/badge/Vite-5.2.0-purple)

这是一个基于 FastAPI 和 React 的全栈Web应用。它允许用户输入一个主题，并调用多个不同的大语言模型（如 Google Gemini, OpenAI GPT）服务来并行生成报告。用户可以浏览和比较各个模型的结果，选择并保存最满意的方案。项目还集成了版本控制、主题分类和基于向量的智能检索功能，能够推荐相似的历史报告。

---

## ✨ 主要功能

- **多模型并行生成**: 输入一个主题，同时向多个配置好的大模型发送请求，获取多样化的报告内容。
- **并排比较与选择**: 在前端清晰地展示来自不同模型的报告，方便用户比较和选择。
- **版本化存储**: 用户选择采纳的方案将被保存，并记录下所用模型、版本、保存时间等元数据。
- **主题分类与历史浏览**: 自动为每次请求分配主题，并提供历史记录页面，让用户可以按主题和时间线回溯查看所有保存过的报告。
- **智能检索推荐**: 当用户输入新主题时，通过句向量技术（Sentence Transformers & ChromaDB）在历史记录中进行语义搜索，并主动推荐最相似的已存报告。
- **安全配置**: 通过 `.env` 文件妥善管理敏感的API密钥，并使用 `.gitignore` 防止其泄露到代码仓库。
- **一键启动**: 提供跨平台的 `concurrently` 脚本和传统的 `.bat`/`.sh` 脚本，简化项目的启动流程。

## 🛠️ 技术栈

- **后端**: Python, FastAPI, Uvicorn
- **前端**: React (使用 Vite), JavaScript, CSS
- **数据库**:
  - **元数据存储**: SQLAlchemy + SQLite (可轻松切换至 PostgreSQL)
  - **向量存储**: ChromaDB (本地运行)
- **AI & ML**:
  - **大语言模型 (LLM)**: Google Gemini, OpenAI GPT
  - **向量嵌入模型**: `sentence-transformers` (`all-MiniLM-L6-v2`)
- **其他工具**:
  - **环境管理**: Conda
  - **进程管理**: `concurrently`

## 🚀 快速开始

请确保您的电脑上已安装 Git, Node.js (v18+), 和 Conda (Miniconda)。

### 1. 克隆仓库

```bash
git clone [https://github.com/YourUsername/YourRepoName.git](https://github.com/YourUsername/YourRepoName.git)
cd YourRepoName
```

### 2. 后端设置

```bash
# 进入后端目录
cd backend

# 创建并激活 Conda 环境
conda create --name report-gen-be python=3.10 -y
conda activate report-gen-be

# (如果还未生成) 生成依赖文件
# pip freeze > requirements.txt

# 安装Python依赖
pip install -r requirements.txt

# 创建环境变量文件
# 复制 .env.example (如果存在) 或手动创建 .env 文件
touch .env
```
然后，编辑 `.env` 文件，填入您的API密钥：
```ini
# backend/.env
OPENAI_API_KEY="sk-..."
GOOGLE_API_KEY="AIzaSy..."
```

### 3. 前端设置
```bash
# 切换到前端目录
cd ../frontend

# 安装Node.js依赖
npm install
```

## ▶️ 运行项目

我们提供了两种启动方式：

### 方案一：一键启动 (推荐)

此方法使用 `concurrently` 并行启动前后端服务。

```bash
# 确保您在 frontend 目录下
npm run start:all
```

### 方案二：手动分别启动

您需要打开两个终端窗口。

**终端1 - 启动后端:**
```bash
# 进入后端目录并激活环境
cd backend
conda activate report-gen-be

# 启动FastAPI服务
uvicorn main:app --reload
```

**终端2 - 启动前端:**
```bash
# 进入前端目录
cd frontend

# 启动React开发服务器
npm run dev
```

项目启动后，请在浏览器中访问 **`http://localhost:5173`** (或您终端中提示的Vite地址)。

---

## 📁 项目结构

```
MultiModelReportGen/
├── .gitignore
├── README.md
├── start_project.sh  # (或 .bat)
├── backend/
│   ├── .env
│   ├── main.py
│   ├── llm_services.py
│   ├── models.py
│   ├── database.py
│   ├── schemas.py
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── main.jsx
    │   ├── ReportGenerator.jsx
    │   └── HistoryPage.jsx
    ├── package.json
    └── ...
```

## 📄 License

本项目采用 [MIT License](LICENSE) 授权。