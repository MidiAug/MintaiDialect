@echo off
chcp 65001 >nul

echo.
echo   ███╗   ███╗██╗███╗   ██╗████████╗ █████╗ ██╗
echo   ████╗ ████║██║████╗  ██║╚══██╔══╝██╔══██╗██║
echo   ██╔████╔██║██║██╔██╗ ██║   ██║   ███████║██║
echo   ██║╚██╔╝██║██║██║╚██╗██║   ██║   ██╔══██║██║
echo   ██║ ╚═╝ ██║██║██║ ╚████║   ██║   ██║  ██║██║
echo   ╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝╚═╝
echo.
echo        闽台方言大模型系统 - 快速启动向导
echo ========================================

echo 欢迎使用闽台方言大模型系统！
echo 这个脚本将帮助您快速设置和启动开发环境。
echo.

set /p choice="是否继续? (Y/N): "
if /i "%choice%"=="N" exit /b 0
if /i "%choice%"=="n" exit /b 0

echo.
echo 🔍 正在检查系统环境...

REM 检查必要软件
set missing_deps=0

where node >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js 未安装
    set missing_deps=1
) else (
    for /f "tokens=*" %%i in ('node --version') do echo ✅ Node.js: %%i
)

where python >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 未安装
    set missing_deps=1
) else (
    for /f "tokens=*" %%i in ('python --version') do echo ✅ Python: %%i
)

where git >nul 2>&1
if errorlevel 1 (
    echo ❌ Git 未安装
    set missing_deps=1
) else (
    for /f "tokens=*" %%i in ('git --version') do echo ✅ Git: %%i
)

if %missing_deps%==1 (
    echo.
    echo ❌ 缺少必要的开发环境，请先安装:
    echo   - Node.js 16+: https://nodejs.org/
    echo   - Python 3.8+: https://python.org/
    echo   - Git: https://git-scm.com/
    echo.
    pause
    exit /b 1
)

echo.
echo 🚀 开始自动安装和配置...

REM 执行依赖安装
call scripts\install-deps.bat
if errorlevel 1 (
    echo ❌ 依赖安装失败
    pause
    exit /b 1
)

echo.
echo 🎯 准备启动开发环境...
timeout /t 3 /nobreak >nul

REM 启动开发环境
call scripts\start-dev.bat

echo.
echo 🎉 快速启动完成！
echo.
echo 感谢使用闽台方言大模型系统！
pause 