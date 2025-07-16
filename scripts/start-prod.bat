@echo off
chcp 65001 >nul

echo 🎤 闽台方言大模型系统 - 生产环境部署
echo ========================================

REM 检查Docker环境
where docker >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker 未安装，请先安装 Docker Desktop
    pause
    exit /b 1
)

where docker-compose >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose 未安装，请先安装 Docker Compose
    pause
    exit /b 1
)

echo ✅ Docker环境检查通过

REM 检查Docker服务是否运行
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker 服务未运行，请启动 Docker Desktop
    pause
    exit /b 1
)

REM 创建必要的目录
echo 创建必要目录...
if not exist "backend\uploads" mkdir backend\uploads
if not exist "backend\logs" mkdir backend\logs
if not exist "backend\models" mkdir backend\models
if not exist "logs" mkdir logs
if not exist "ssl" mkdir ssl

REM 构建并启动服务
echo.
echo 🚀 构建并启动生产环境...
docker-compose down
docker-compose build --no-cache
docker-compose up -d

REM 等待服务启动
echo 等待服务启动...
timeout /t 30 /nobreak >nul

REM 检查服务状态
echo.
echo 📊 检查服务状态...
docker-compose ps

REM 检查后端健康状态
echo.
echo 🔍 检查服务健康状态...

REM 使用PowerShell检查HTTP状态 (Windows内置)
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8000/api/health' -UseBasicParsing -TimeoutSec 5; if ($response.StatusCode -eq 200) { Write-Host '✅ 后端API服务正常' } else { Write-Host '❌ 后端API服务异常' } } catch { Write-Host '❌ 后端API服务异常' }"

powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:3000' -UseBasicParsing -TimeoutSec 5; if ($response.StatusCode -eq 200) { Write-Host '✅ 前端服务正常' } else { Write-Host '❌ 前端服务异常' } } catch { Write-Host '❌ 前端服务异常' }"

echo.
echo 🎉 生产环境启动完成！
echo ========================================
echo 🌐 应用访问地址: http://localhost:3000
echo 🔌 API服务地址: http://localhost:8000
echo 📚 API文档: http://localhost:8000/docs
echo.
echo 📝 查看日志:
echo    所有服务: docker-compose logs
echo    后端日志: docker-compose logs backend
echo    前端日志: docker-compose logs frontend
echo.
echo ⏹️  停止服务: docker-compose down
echo 🔄 重启服务: docker-compose restart
echo ========================================

pause 