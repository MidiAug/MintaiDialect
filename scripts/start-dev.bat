@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo 🎤 闽台方言大模型系统 - 开发环境启动
echo ========================================

REM 检查Node.js和Python环境
echo 检查环境依赖...

REM 检查Node.js
where node >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js 未安装，请先安装 Node.js 16+
    pause
    exit /b 1
)

REM 检查Python
where python >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 未安装，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo ✅ 环境检查通过

REM 创建日志目录
if not exist "logs" mkdir logs

REM 启动后端服务
echo.
echo 🚀 启动后端服务...
cd backend

REM 检查Python虚拟环境
if not exist "venv" (
    echo 创建Python虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ 创建虚拟环境失败
        pause
        exit /b 1
    )
)

REM 激活虚拟环境
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ 激活虚拟环境失败
    pause
    exit /b 1
)

REM 安装依赖
echo 安装Python依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 安装Python依赖失败
    pause
    exit /b 1
)

REM 创建必要目录
if not exist "uploads" mkdir uploads
if not exist "logs" mkdir logs
if not exist "cache" mkdir cache
if not exist "models" mkdir models

REM 复制环境变量文件
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo ✅ 已创建 .env 文件，请根据需要修改配置
    )
)

REM 启动后端服务 (后台运行)
echo 启动FastAPI后端服务...
start "MinTai Backend" cmd /k "venv\Scripts\activate.bat && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

REM 等待后端启动
echo 等待后端服务启动...
timeout /t 5 /nobreak >nul

cd ..

REM 启动前端服务
echo.
echo 🎨 启动前端服务...
cd frontend

REM 检查是否已安装依赖
if not exist "node_modules" (
    echo 安装Node.js依赖...
    npm install
    if errorlevel 1 (
        echo ❌ 安装Node.js依赖失败
        pause
        exit /b 1
    )
) else (
    echo Node.js依赖已存在，跳过安装...
)

REM 启动前端服务
echo 启动React开发服务器...
start "MinTai Frontend" cmd /k "npm run dev"

cd ..

echo.
echo 🎉 启动完成！
echo ========================================
echo 📖 前端应用: http://localhost:5173
echo 🔌 后端API: http://localhost:8000
echo 📚 API文档: http://localhost:8000/docs
echo.
echo 📝 日志信息:
echo    后端日志: 查看后端窗口
echo    前端日志: 查看前端窗口
echo.
echo ⏹️  停止服务: 关闭窗口或运行 scripts\stop-dev.bat
echo ========================================

echo 服务已启动，按任意键关闭此窗口...
pause >nul 