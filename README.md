# Mini-OpenClaw

基于 Python 重构的、轻量级且高度透明的 AI Agent 系统，旨在复刻并优化 OpenClaw(原名 Moltbot/Clawdbot)的核心体验。

## 核心特性

- **文件即记忆 (File-first Memory)**：摒弃不透明的向量数据库，回归最原始、最通用的 Markdown/JSON 文件系统。
- **技能即插件 (Skills as Plugins)**：遵循 Anthropic 的 Agent Skills 范式，通过文件夹结构管理能力。
- **透明可控**：所有的 System Prompt 拼接逻辑、工具调用过程、记忆读写操作对开发者完全透明。
- **多用户支持**：实现了用户注册、登录和会话管理功能，支持多用户使用。
- **PostgreSQL 存储**：使用 PostgreSQL 存储会话信息，确保数据持久化。
- **Redis 缓存**：使用 Redis 存储用户令牌，提升认证性能。

## 技术架构

### 后端
- **语言**：Python 3.10+
- **框架**：FastAPI
- **Agent 编排**：LangChain 1.x + LangGraph
- **RAG 检索**：LlamaIndex
- **数据库**：PostgreSQL
- **缓存**：Redis
- **模型接口**：兼容 OpenAI API 格式

### 前端
- **框架**：Next.js 14+ (App Router)
- **语言**：TypeScript
- **UI**：Tailwind CSS、Lucide Icons
- **编辑器**：Monaco Editor

## 目录结构

```
mini-openclaw/
├── PRD/ # 产品需求文档
├── backend/ # FastAPI + LangChain/LangGraph
│   ├── api/ # API 路由
│   │   ├── login.py # 登录相关接口
│   │   └── user.py # 用户管理接口
│   ├── memory/ # 记忆存储
│   │   ├── logs/ # Daily logs
│   │   └── MEMORY.md # Core memory
│   ├── sessions/ # 会话记录
│   ├── skills/ # Agent Skills 文件夹
│   │   ├── docker-desktop_windows_operation_guide/ # Docker 操作技能
│   │   ├── get_weather/ # 天气查询技能
│   │   └── summarization_skill/ # 文本摘要技能
│   ├── tools/ # Core Tools 实现
│   ├── utils/ # 工具函数
│   │   ├── config.py # 配置管理
│   │   ├── db_init.py # 数据库初始化
│   │   ├── logger.py # 日志管理
│   │   └── middleware.py # 认证中间件
│   ├── workspace/ # System Prompts
│   │   ├── AGENTS.md # 行为准则
│   │   ├── IDENTITY.md # 自我认知
│   │   ├── SOUL.md # 核心设定
│   │   └── USER.md # 用户画像
│   ├── app.py # 入口文件 (invoke式，AI/USER消息)
│   ├── app_t.py # 入口文件2 (流式，AI/USER/TOOL消息)
│   ├── requirements.txt # 依赖管理
│   └── SKILLS_SNAPSHOT.md # 技能快照
├── frontend/ # Next.js 14+
│   ├── src/
│   │   ├── app/ # 应用入口
│   │   └── components/ # 组件
│   │       ├── AppContent.tsx # 主应用组件
│   │       ├── LoginForm.tsx # 登录表单
│   │       └── UserSettings.tsx # 用户设置
│   ├── package.json # 前端依赖
│   └── tailwind.config.js # Tailwind 配置
├── .env.example # 环境变量示例
└── README.md # 项目说明
```

## 核心工具

1. **命令行操作工具 (terminal)**：执行 Shell 命令
2. **Python 代码解释器 (python_repl)**：运行 Python 代码
3. **网络信息获取 (fetch_url)**：获取网页内容并转换为 Markdown
4. **文件读取工具 (read_file)**：读取本地文件
5. **RAG 检索工具 (search_knowledge_base)**：检索知识库信息

## Agent Skills 系统

Mini-OpenClaw 的 Agent Skills 遵循 **"Instruction-following" (指令遵循)** 范式，技能以文件夹形式存在于 `backend/skills/` 目录下。

### 技能调用流程
1. Agent 在 System Prompt 中看到 available_skills 列表
2. 当用户请求匹配某个技能时，Agent 使用 `read_file` 工具读取技能的 Markdown 文件
3. Agent 理解操作步骤，然后调用 Core Tools 来完成任务

## 对话记忆管理

所有记忆文件(Markdown/JSON)均存储在本地文件系统，确保完全的数据主权和可解释性。

### System Prompt 构成
1. SKILLS_SNAPSHOT.md (能力列表)
2. SOUL.md (核心设定)
3. IDENTITY.md (自我认知)
4. USER.md (用户画像)
5. AGENTS.md (行为准则 & 记忆操作指南)
6. MEMORY.md (长期记忆)

## API 接口

### 认证接口
- **POST /api/login**：用户登录
- **POST /api/user/register**：用户注册
- **DELETE /api/logout**：用户登出
- **POST /api/user/update-username**：修改用户名
- **POST /api/user/update-password**：修改密码
- **GET /api/user/info**：获取用户信息

### 核心对话接口
- **Endpoint**：POST /api/chat
- **功能**：发送用户消息，获取 Agent 回复
- **支持 SSE 流式输出**：实时推送 Agent 的思考过程和最终回复

### 文件管理接口
- **GET /api/files**：读取指定文件的内容
- **POST /api/files**：保存对 Memory 或 Skill 文件的修改

### 会话管理接口
- **GET /api/sessions**：获取用户的会话列表
- **POST /api/sessions**：创建新会话
- **DELETE /api/sessions/{session_id}**：删除指定会话
- **POST /api/sessions/{session_id}/rename**：重命名指定会话
- **GET /api/history/{session_id}**：获取指定会话的历史消息

### 技能管理接口
- **GET /api/skills/list**：列出所有可用技能

## 前端界面

前端采用 IDE(集成开发环境)风格，**三栏式布局**：

- **左侧 (Sidebar)**：导航 (Chat/Memory/Skills) + 会话列表
- **中间 (Stage)**：对话流 + 思考链可视化
- **右侧 (Inspector)**：Monaco Editor，用于实时查看/编辑正在使用的 SKILL.md 或 MEMORY.md

### 用户管理功能
- **登录/注册**：用户认证系统
- **用户设置**：修改用户名和密码
- **会话管理**：创建、删除、重命名会话

## 快速开始

### 环境准备
1. 安装 PostgreSQL 数据库
2. 安装 Redis 服务
3. 配置环境变量（参考 .env.example 文件）

### 后端启动
1. 进入 backend 目录
2. 安装依赖：`pip install -r requirements.txt`
3. 启动服务：`python app_t.py`

### 前端启动
1. 进入 frontend 目录
2. 安装依赖：`npm install`
3. 启动开发服务器：`npm run dev`

### 访问应用
- 前端：http://localhost:3000
- 后端 API：http://localhost:8002

## 配置说明

### 环境变量
- `MODEL`：模型名称
- `BASE_URL`：模型接口的基础 URL
- `API_KEY`：模型接口的 API Key

### Config配置
- `DATABASE_URL`：PostgreSQL 数据库连接 URL
- `REDIS_HOST`：Redis 服务器地址
- `REDIS_PORT`：Redis 服务器端口

### 数据库配置
1. PostgreSQL 数据库需要创建相应的表结构
2. 系统启动时会自动初始化数据库表结构
3. 默认会创建两个测试用户：
   - 用户名：admin，密码：1234
   - 用户名：user1，密码：654321

### 技能开发
1. 在 `backend/skills/` 目录下创建新的技能文件夹
2. 在文件夹中创建 `SKILL.md` 文件，包含技能的描述、步骤和示例
3. 重启后端服务，技能会自动加载到系统中

## 注意事项

- 本项目使用本地文件系统存储数据，请确保有足够的权限
- 核心工具中的终端操作有沙箱限制，只能在指定目录内操作
- 首次启动时会自动生成必要的配置文件和目录结构
- RAG 检索功能需要先在 `knowledge/` 目录下添加文档

## 部署指南

### 后端部署
1. 使用 Gunicorn + Uvicorn 作为 WSGI 服务器
2. 配置 Nginx 作为反向代理
3. 使用 Supervisor 管理进程

### 前端部署
1. 执行 `npm run build` 构建生产版本
2. 使用 Nginx 部署静态文件
3. 配置 Nginx 反向代理到后端 API

## 故障排除

### 常见问题
1. **数据库连接失败**：检查 PostgreSQL 服务是否运行，连接字符串是否正确
2. **Redis 连接失败**：检查 Redis 服务是否运行，配置是否正确
3. **模型接口错误**：检查 API Key 和 Base URL 是否正确
4. **前端无法访问后端**：检查 CORS 配置，确保前端域名在允许列表中

### 日志管理
- 后端日志位于 `backend/logs/` 目录
- 前端日志可在浏览器控制台查看

## 未来规划

- 支持更多模型接口
- 增强技能系统，支持更复杂的任务
- 优化前端界面，提升用户体验
- 添加更多核心工具和示例技能
- 实现更高级的记忆管理策略
- 支持多语言
- 添加更多用户管理功能
- 实现数据备份和恢复功能