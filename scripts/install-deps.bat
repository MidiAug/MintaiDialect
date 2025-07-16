@echo off
chcp 65001 >nul

echo 🔧 闽台方言大模型系统 - 依赖安装
echo ========================================

REM 检查环境
echo 检查开发环境...

where node >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js 未安装
    echo 请从 https://nodejs.org/ 下载并安装 Node.js 16+
    pause
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('node --version') do echo ✅ Node.js: %%i
)

where python >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 未安装
    echo 请从 https://python.org/ 下载并安装 Python 3.8+
    pause
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('python --version') do echo ✅ Python: %%i
)

where git >nul 2>&1
if errorlevel 1 (
    echo ❌ Git 未安装
    echo 请从 https://git-scm.com/ 下载并安装 Git
    pause
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('git --version') do echo ✅ Git: %%i
)

echo.
echo 🚀 开始安装项目依赖...

REM 安装后端依赖
echo.
echo 📦 安装后端Python依赖...
cd backend

if not exist "venv" (
    echo 创建Python虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ 创建虚拟环境失败
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 安装Python依赖失败
    pause
    exit /b 1
)

cd ..

REM 安装前端依赖
echo.
echo 🎨 安装前端Node.js依赖...
cd frontend

npm install
if errorlevel 1 (
    echo ❌ 安装Node.js依赖失败
    pause
    exit /b 1
)

cd ..

REM 创建必要目录
echo.
echo 📁 创建项目目录...
if not exist "logs" mkdir logs
if not exist "backend\uploads" mkdir backend\uploads
if not exist "backend\logs" mkdir backend\logs
if not exist "backend\cache" mkdir backend\cache
if not exist "backend\models" mkdir backend\models

REM 复制配置文件
echo.
echo ⚙️ 创建配置文件...
if not exist "backend\.env" (
    if exist "backend\.env.example" (
        copy "backend\.env.example" "backend\.env" >nul
        echo ✅ 已创建后端 .env 配置文件
    )
)

if not exist "frontend\.env" (
    echo VITE_API_BASE_URL=http://localhost:8000 > "frontend\.env"
    echo VITE_APP_TITLE=闽台方言大模型系统 >> "frontend\.env"
    echo ✅ 已创建前端 .env 配置文件
)

echo.
echo 🎉 依赖安装完成！
echo ========================================
echo ✅ 后端Python依赖已安装
echo ✅ 前端Node.js依赖已安装
echo ✅ 项目目录已创建
echo ✅ 配置文件已生成
echo.
echo 📖 下一步操作:
echo    开发环境: scripts\start-dev.bat
echo    生产环境: scripts\start-prod.bat
echo ========================================

pause 