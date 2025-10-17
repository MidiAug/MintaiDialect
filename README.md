# 闽台方言大模型系统

一个基于人工智能的闽台方言语音处理平台，支持语音识别、文本转语音、语音翻译、智能对话和音色克隆等功能。

### 最新更新（2025-08）

- 数字嘉庚模块体验优化：
  - TTS 缓存稳定化（基于 `speaking_rate|seed|text` 的 SHA1 摘要）。
  - TTS 文本切分更稳（显式标点集合逐字符切句）。
  - 字幕时间更准（静音边界拟合 + 起声补偿 + 保守回退，避免错误合段）。
  - 播放与资源优化（新音频播放前暂停旧音频、关闭临时 AudioContext）。
  - 端口约定统一：ASR=9000、TTS=9002、LLM=9001（均可通过环境变量覆盖）。

## 📖 项目概述

本项目旨在为闽台方言提供全面的AI语音处理解决方案，具备以下核心功能：

### 🎯 核心功能

1. **语音文本互转 (ASR/TTS)**
   - 高精度方言语音识别
   - 自然的方言语音合成
   - 支持多种音频格式
   - 提供时间戳和词级别信息

2. **语音翻译**
   - 方言与普通话双向翻译
   - 实时语音翻译
   - 智能语言检测
   - 翻译质量评估

3. **智能语音交互**
   - 多轮对话理解
   - 方言问答系统
   - 情感和意图识别
   - 语音和文本双模态交互

4. **音色克隆**
   - 文本驱动音色克隆
   - 音频驱动音色转换
   - 音色相似度分析
   - 语音特征提取

## 🛠 技术栈

### 前端技术
- **React 18** - 现代前端框架
- **TypeScript** - 类型安全的JavaScript
- **Vite** - 快速构建工具
- **Ant Design** - 企业级UI组件库
- **Axios** - HTTP客户端

### 后端技术
- **FastAPI** - 高性能Python Web框架
- **Pydantic** - 数据验证和设置管理
- **Uvicorn** - ASGI服务器
- **SQLite** - 轻量级数据库

### AI/音频处理
- **PyTorch** - 深度学习框架
- **Transformers (HuggingFace)** - 预训练模型库（TTS: VITS `facebook/mms-tts-nan`）
- **ModelScope** - 语音识别（ASR：`speech_UniASR_asr_2pass-minnan-16k`）
- **Librosa / SoundFile** - 音频分析与文件处理（可选）

## 🚀 快速开始

### 环境要求

- **Node.js**: 16.0+ 
- **Python**: 3.8+
- **Git**: 最新版本

### 本地开发

1. **克隆项目**
```bash
git clone <项目地址>
cd MintaiDialect
```

2. **一键启动开发环境**

**Windows用户 (推荐)**
```cmd
# 快速启动向导 (首次使用推荐)
scripts\quick-start.bat

# 或者直接启动开发环境
scripts\start-dev.bat
```

**Linux/macOS用户**
```bash
# 给脚本添加执行权限
chmod +x scripts/*.sh

# 启动开发环境
./scripts/start-dev.sh
```

3. **手动启动 (可选)**

**启动后端**
```bash
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/macOS
source venv/bin/activate
# Windows
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**启动前端**
```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

4. **访问应用**
- 前端应用: http://localhost:5173
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

### 启动独立模型微服务（本地调试）

提供脚本分别启动 ASR/TTS/LLM 微服务（默认端口：ASR=9000、TTS=9002、LLM=9001）：

```bash
# TTS（facebook/mms-tts-nan）
bash scripts/single/start-tts.sh             # 可用 PORT/WORKERS 覆盖

# LLM（示例服务）
bash scripts/single/start-llm.sh

# ASR（闽南话 16k）
bash scripts/single/start-asr.sh

# 前端开发
bash scripts/single/start-frontend.sh
```

后端默认从环境变量读取这些服务地址（见“环境变量”），未配置时：
- ASR: `http://127.0.0.1:9000`
- TTS: `http://127.0.0.1:9002`
- LLM: 留空则走云厂商（DeepSeek）；设置 `LLM_SERVICE_URL` 可改为本地服务（如 `http://127.0.0.1:9001`）。

> 小贴士（验证 TTS 缓存命中）：
```bash
curl -s -o uploads/test1.wav "http://127.0.0.1:9002/tts?text=你好，欢迎使用数字嘉庚&speaking_rate=0.9&seed=42"
curl -s -o uploads/test2.wav "http://127.0.0.1:9002/tts?text=你好，欢迎使用数字嘉庚&speaking_rate=0.9&seed=42"
# 第二次应看到 [TTS] cache hit 日志
```

## 🪟 Windows开发指南

### 快速开始 (推荐)

对于Windows用户，我们提供了友好的图形化脚本：

```cmd
# 1. 快速启动向导 (首次使用)
scripts\quick-start.bat
```

这个脚本会：
- ✅ 自动检查开发环境
- ✅ 安装所有依赖
- ✅ 创建配置文件
- ✅ 启动开发服务

### 分步操作

如果您希望分步执行：

```cmd
# 1. 安装项目依赖
scripts\install-deps.bat

# 2. 启动开发环境
scripts\start-dev.bat

# 3. 停止开发环境
scripts\stop-dev.bat
```

### Windows常见问题

1. **Python虚拟环境问题**
   ```cmd
   # 如果遇到激活虚拟环境失败，请以管理员身份运行
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

2. **端口占用问题**
   ```cmd
   # 查看端口占用
   netstat -ano | findstr :8000
   netstat -ano | findstr :5173
   
   # 结束占用进程
   taskkill /PID <进程ID> /F
   ```

3. **Node.js权限问题**
   ```cmd
   # 清理npm缓存
   npm cache clean --force
   
   # 重新安装依赖
   npm install
   ```

## 📦 生产部署

### Docker部署 (推荐)

1. **构建并启动**

**Windows**
```cmd
# 一键部署
scripts\start-prod.bat

# 或手动执行
docker-compose up -d --build
```

**Linux/macOS**
```bash
# 一键部署
./scripts/start-prod.sh

# 或手动执行
docker-compose up -d --build
```

2. **访问应用**
- 应用地址: http://localhost:3000
- API地址: http://localhost:8000

### （可选）在生产中运行模型微服务

若要在同一编排中运行 ASR/TTS/LLM，可在 `docker-compose.yml` 增加服务并为后端注入地址：

```yaml
services:
  tts-service:
    image: your-tts-image
    ports: ["9002:9002"]
  llm-service:
    image: your-llm-image
    ports: ["9001:9001"]
  asr-service:
    image: your-asr-image
    ports: ["9000:9000"]
  backend:
    environment:
      - ASR_SERVICE_URL=http://asr-service:9000
      - TTS_SERVICE_URL=http://tts-service:9002
      - LLM_SERVICE_URL=http://llm-service:9001
```

### 传统部署

1. **后端部署**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

2. **前端部署**
```bash
cd frontend
npm install
npm run build
# 将 dist 目录部署到 web 服务器
```

## 📁 项目结构

```
MintaiDialect/
├── README.md                 # 项目说明文档
├── docker-compose.yml        # Docker编排配置
├── scripts/                  # 部署脚本
│   ├── start-dev.sh         # Linux/macOS开发环境启动
│   ├── start-dev.bat        # Windows开发环境启动
│   ├── stop-dev.sh          # Linux/macOS开发环境停止
│   ├── stop-dev.bat         # Windows开发环境停止
│   ├── start-prod.sh        # Linux/macOS生产环境启动
│   ├── start-prod.bat       # Windows生产环境启动
│   ├── install-deps.bat     # Windows依赖安装
│   └── quick-start.bat      # Windows快速启动向导
├── backend/                  # 后端代码
│   ├── Dockerfile           # 后端Docker配置
│   ├── requirements.txt     # Python依赖
│   ├── .env.example         # 环境变量示例
│   └── app/                 # 应用代码
│       ├── main.py          # 主应用入口
│       ├── core/            # 核心配置
│       ├── models/          # 数据模型
│       └── routers/         # API路由
└── frontend/                # 前端代码
    ├── Dockerfile           # 前端Docker配置
    ├── package.json         # 项目依赖
    ├── vite.config.ts       # Vite配置
    ├── src/                 # 源代码
    │   ├── pages/           # 页面组件
    │   ├── components/      # 公共组件
    │   ├── services/        # API服务
    │   └── main.tsx         # 应用入口
    └── public/              # 静态资源
```

## 🔧 配置说明

### 后端配置

在 `backend/.env` 文件中配置以下参数：

```env
# 应用配置
APP_NAME=闽台方言大模型API
DEBUG=true

# 文件上传
MAX_FILE_SIZE=52428800  # 50MB
UPLOAD_DIR=uploads

# CORS设置
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# 外部微服务/云厂商（按需覆盖）
ASR_SERVICE_URL=http://127.0.0.1:9000
TTS_SERVICE_URL=http://127.0.0.1:9002
# 若启用本地 LLM 服务：
# LLM_SERVICE_URL=http://127.0.0.1:9001
PROVIDER_NAME=deepseek
# 生产环境请设置为真实密钥：
# PROVIDER_API_KEY=sk-***
DEEPSEEK_API_BASE=https://api.deepseek.com
LLM_MODEL_NAME=deepseek-chat
GEMINI_API_BASE=https://generativelanguage.googleapis.com/v1beta
```

### 前端配置

在 `frontend/.env` 文件中配置：

```env
# API地址
VITE_API_BASE_URL=http://localhost:8000

# 应用信息
VITE_APP_TITLE=闽台方言大模型系统
```

## 🎮 功能使用

### 1. 语音文本互转
- 上传音频文件进行语音识别
- 输入文本进行语音合成
- 支持闽南话、客家话、台湾话、普通话

### 2. 语音翻译
- 上传方言音频进行翻译
- 支持双向翻译（方言↔普通话）
- 提供翻译质量评分

### 3. 智能对话
- 与AI进行自然语言对话
- 支持语音和文本输入
- 方言文化知识问答

#### 数字嘉庚（DigitalJiageng）
- 语音输入后：ASR → LLM → TTS，返回音频与可选字幕。
- 前端播放：
  - 初始按文本等分生成字幕；
  - 自动分析音频静音边界并对每句时间轴拟合；
  - 起声时间进行保守整体提前补偿（≤ 0.15s）；
  - 拟合质量不足则回退到等分方案，避免字幕合并。

### 4. 音色克隆
- 基于参考音频克隆音色
- 文本驱动和音频驱动两种模式
- 音色相似度分析

## 🔍 API文档

启动后端服务后，访问 http://localhost:8000/docs 查看完整的API文档。

### 主要API端点

- `POST /api/asr/speech-to-text` - 语音识别
- `POST /api/tts/text-to-speech` - 文本转语音
- `POST /api/translation/translate-speech` - 语音翻译
- `POST /api/interaction/voice-chat` - 语音对话
- `POST /api/cloning/text-driven` - 文本驱动克隆

## 🧪 开发说明

### 开发模式
- 后端支持热重载，修改代码后自动重启
- 前端支持HMR，修改后即时更新
- API接口采用Mock数据，方便前端开发

### 代码规范
- 使用TypeScript增强类型安全
- 遵循React Hooks最佳实践
- API响应统一格式
- 完善的错误处理机制

### 测试
```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
npm test
```

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- 感谢开源社区提供的优秀工具和框架
- 感谢所有为方言保护和传承做出贡献的人

## 📞 联系我们

- 项目主页: [GitHub Repository]
- 问题反馈: [GitHub Issues]
- 邮箱: contact@mintaidialect.com

---

**注意**: 本项目中的AI模型接口为演示版本，实际部署时需要配置相应的模型文件和API密钥。 