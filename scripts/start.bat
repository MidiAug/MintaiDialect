@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM MintaiDialect start script
REM Support local start and Docker start
REM Auto-check and activate Conda env: MintaiDialect

REM 检测并关闭已运行的服务
call :check_and_close_running_services

if "%1"=="--help" goto :help
if "%1"=="-h" goto :help
if "%1"=="--docker" goto :docker
if "%1"=="-d" goto :docker
if "%1"=="--local" goto :local
if "%1"=="-l" goto :local

REM 默认显示选择菜单
:menu
echo.
echo 🚀 闽台方言大模型启动脚本
echo ================================
echo.
echo 请选择启动方式：
echo.
echo 1. 本地启动（推荐开发环境）
echo 2. Docker启动（推荐生产环境）
echo 3. 查看帮助
echo 4. 退出
echo.
set /p choice="请输入选择 (1-4): "
echo.
if "%choice%"=="1" goto :local
if "%choice%"=="2" goto :docker
if "%choice%"=="3" goto :help
if "%choice%"=="4" goto :end
echo 无效选择，请重新输入
goto :menu

:local
echo.
echo 使用本地环境启动服务...
echo.
echo 检查MintaiDialect环境...
conda env list | findstr "MintaiDialect" >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到MintaiDialect环境，请先运行 install.bat
    pause
    exit /b 1
)
echo ✅ 找到MintaiDialect环境

echo 启动后端服务（MintaiDialect）...
start "后端服务 - MintaiDialect环境" cmd /k "title 后端服务 - MintaiDialect环境 & cd backend & call conda activate MintaiDialect & set PYTHONPATH=. & uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo.
echo ⏳ 等待后端启动...
timeout /t 5 /nobreak >nul
echo.
echo 启动前端服务（Vite）...
start "前端服务 - Vite开发服务器" cmd /k "title 前端服务 - Vite开发服务器 & cd frontend & npm run dev"

echo.
echo ✅ 本地服务启动完成！
echo 🌐 前端地址: http://localhost:5173
echo 🔧 后端地址: http://localhost:8000
echo 📚 API文档: http://localhost:8000/docs
echo.
echo 💡 提示: 后端服务已在MintaiDialect环境中启动
echo 💡 提示: 关闭服务请关闭对应的命令行窗口
pause
goto :end

:docker
echo.
echo 🐳 使用Docker启动服务...
echo.
echo 🔨 构建Docker镜像...
docker-compose build
echo.
echo 🚀 启动Docker服务...
docker-compose up -d
echo.
echo ✅ Docker服务启动完成！
echo 🌐 前端地址: http://localhost:5173
echo 🔧 后端地址: http://localhost:8000
echo 📚 API文档: http://localhost:8000/docs
pause
goto :end

:help
echo.
echo 📖 闽台方言大模型启动脚本帮助
echo ================================
echo.
echo 用法: start.bat [选项]
echo.
echo 选项:
echo   --local, -l    本地启动（开发环境）
echo   --docker, -d   Docker启动（生产环境）
echo   --help, -h     显示此帮助信息
echo.
echo 本地启动说明:
echo   - 自动检测并激活MintaiDialect环境
echo   - 后端服务在MintaiDialect环境中运行
echo.
pause
goto :end

:end
echo.
echo 👋 感谢使用闽台方言大模型！
exit /b 0

REM 检测并关闭已运行的服务函数
:check_and_close_running_services
echo 🔍 检查并关闭已运行的服务...

REM 1) 先按窗口标题直接关闭（适用于独立 cmd 窗口）
taskkill /f /fi "WINDOWTITLE eq 后端服务 - MintaiDialect环境*" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq 前端服务 - Vite开发服务器*" >nul 2>&1

REM 2) 按端口强制关闭（更稳妥，适用于在 Windows Terminal 等环境中启动的进程）
call :kill_by_port 8000
call :kill_by_port 5173

echo ✅ 清理完成
echo.
goto :eof

REM 旧的按标题关闭函数已不再使用（在部分控制台环境中可能产生解析问题）

REM 通过端口号关闭占用进程（如 uvicorn、vite）
:kill_by_port
setlocal ENABLEDELAYEDEXPANSION
set "PORT=%~1"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
    set "PID=%%P"
    if not "!PID!"=="" (
        echo 🚫 关闭占用端口 !PORT! 的进程 → PID !PID!
        taskkill /f /pid !PID! >nul 2>&1
    )
)
REM 兜底：某些系统的 findstr 正则支持有限，使用两次筛选
for /f "tokens=5" %%P in ('cmd /c "netstat -ano | findstr ":%PORT% " | findstr /i LISTENING"') do (
    set "PID=%%P"
    if not "!PID!"=="" (
        echo 🚫 关闭占用端口 !PORT! 的进程 → PID !PID!
        taskkill /f /pid !PID! >nul 2>&1
    )
)
endlocal
goto :eof
