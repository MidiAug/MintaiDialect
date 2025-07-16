@echo off
chcp 65001 >nul

echo ⏹️  停止闽台方言大模型系统开发服务...

REM 停止后端服务
echo 停止后端服务...
taskkill /f /im "uvicorn.exe" 2>nul
taskkill /f /im "python.exe" /fi "WINDOWTITLE eq MinTai Backend*" 2>nul

REM 停止前端服务
echo 停止前端服务...
taskkill /f /im "node.exe" /fi "WINDOWTITLE eq MinTai Frontend*" 2>nul

REM 更广泛地清理Node.js和Python进程
echo 清理相关进程...

REM 查找并终止包含uvicorn的进程
for /f "tokens=2" %%i in ('tasklist /fi "imagename eq python.exe" /fo csv ^| findstr "uvicorn"') do (
    taskkill /f /pid %%i 2>nul
)

REM 查找并终止包含vite dev的Node.js进程
for /f "tokens=2" %%i in ('tasklist /fi "imagename eq node.exe" /fo csv ^| findstr "vite"') do (
    taskkill /f /pid %%i 2>nul
)

REM 关闭相关的命令行窗口
taskkill /f /fi "WINDOWTITLE eq MinTai Backend*" 2>nul
taskkill /f /fi "WINDOWTITLE eq MinTai Frontend*" 2>nul

echo ✅ 所有服务已停止

timeout /t 2 /nobreak >nul 