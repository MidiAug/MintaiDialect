@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo 🚀 开始安装闽台方言大模型项目...
echo ===============================================

REM 检查PowerShell是否可用
powershell -Command "Write-Host 'PowerShell可用'" >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误：PowerShell不可用，请安装PowerShell 5.0+
    pause
    exit /b 1
)

REM 检查是否以管理员身份运行
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  警告：建议以管理员身份运行此脚本以获得最佳体验
    echo.
)

echo 🔍 检查系统依赖...

REM 检查Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python未安装，正在下载并安装...
    
    REM 下载Python安装程序
    set "pythonUrl=https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe"
    set "pythonInstaller=%TEMP%\python-installer.exe"
    
    echo 📥 下载Python安装程序...
    powershell -Command "Invoke-WebRequest -Uri '%pythonUrl%' -OutFile '%pythonInstaller%'"
    
    if exist "%pythonInstaller%" (
        echo 📦 安装Python...
        "%pythonInstaller%" /quiet InstallAllUsers=1 PrependPath=1
        echo ✅ Python安装完成
        
        REM 刷新环境变量
        call refreshenv.cmd 2>nul || (
            echo 请重新打开命令提示符以使环境变量生效
        )
    ) else (
        echo ❌ Python下载失败
        echo 请手动安装Python 3.11+并重新运行脚本
        pause
        exit /b 1
    )
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "pythonVersion=%%i"
    echo ✅ Python已安装：!pythonVersion!
)

REM 检查Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js未安装，正在下载并安装...
    
    REM 下载Node.js安装程序
    set "nodeUrl=https://nodejs.org/dist/v18.17.0/node-v18.17.0-x64.msi"
    set "nodeInstaller=%TEMP%\node-installer.msi"
    
    echo 📥 下载Node.js安装程序...
    powershell -Command "Invoke-WebRequest -Uri '%nodeUrl%' -OutFile '%nodeInstaller%'"
    
    if exist "%nodeInstaller%" (
        echo 📦 安装Node.js...
        msiexec /i "%nodeInstaller%" /quiet /norestart
        echo ✅ Node.js安装完成
        
        REM 刷新环境变量
        call refreshenv.cmd 2>nul || (
            echo 请重新打开命令提示符以使环境变量生效
        )
    ) else (
        echo ❌ Node.js下载失败
        echo 请手动安装Node.js 18+并重新运行脚本
        pause
        exit /b 1
    )
) else (
    for /f "tokens=1" %%i in ('node --version 2^>^&1') do set "nodeVersion=%%i"
    echo ✅ Node.js已安装：!nodeVersion!
)

REM 检查Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Git未安装，正在下载并安装...
    
    REM 下载Git安装程序
    set "gitUrl=https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe"
    set "gitInstaller=%TEMP%\git-installer.exe"
    
    echo 📥 下载Git安装程序...
    powershell -Command "Invoke-WebRequest -Uri '%gitUrl%' -OutFile '%gitInstaller%'"
    
    if exist "%gitInstaller%" (
        echo 📦 安装Git...
        "%gitInstaller%" /VERYSILENT /NORESTART
        echo ✅ Git安装完成
        
        REM 刷新环境变量
        call refreshenv.cmd 2>nul || (
            echo 请重新打开命令提示符以使环境变量生效
        )
    ) else (
        echo ❌ Git下载失败
        echo 请手动安装Git并重新运行脚本
        pause
        exit /b 1
    )
) else (
    for /f "tokens=3" %%i in ('git --version 2^>^&1') do set "gitVersion=%%i"
    echo ✅ Git已安装：!gitVersion!
)

REM 检查Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Docker未安装，建议安装Docker Desktop以获得最佳体验
    echo    您可以从 https://www.docker.com/products/docker-desktop 下载
) else (
    for /f "tokens=3" %%i in ('docker --version 2^>^&1') do set "dockerVersion=%%i"
    echo ✅ Docker已安装：!dockerVersion!
)

echo.
echo 📁 创建项目目录结构...

REM 创建必要目录
set "directories=backend\uploads backend\logs backend\models backend\cache logs scripts"
for %%d in (%directories%) do (
    if not exist "%%d" (
        mkdir "%%d" 2>nul
        echo ✅ 创建目录：%%d
    ) else (
        echo ℹ️  目录已存在：%%d
    )
)

echo.
echo 🐍 安装Python依赖...

REM 检查conda是否可用
conda --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Conda未安装，请先安装Anaconda或Miniconda
    echo 下载地址：https://docs.conda.io/en/latest/miniconda.html
    pause
    exit /b 1
) else (
    for /f "tokens=1" %%i in ('conda --version 2^>^&1') do set "condaVersion=%%i"
    echo ✅ Conda已安装：!condaVersion!
)

REM 检查并创建MintaiDialect环境
echo 🔍 检查MintaiDialect环境...
conda env list | findstr "MintaiDialect" >nul 2>&1
if errorlevel 1 (
    echo 📦 创建MintaiDialect环境...
    conda create -n MintaiDialect python=3.11 -y
    if errorlevel 1 (
        echo ❌ 环境创建失败
        pause
        exit /b 1
    )
    echo ✅ MintaiDialect环境创建成功
) else (
    echo ✅ MintaiDialect环境已存在
)

REM 激活MintaiDialect环境并安装依赖
echo 📦 激活MintaiDialect环境并安装Python包...
call conda activate MintaiDialect
if errorlevel 1 (
    echo ❌ 环境激活失败，尝试使用备用方法...
    call conda run -n MintaiDialect pip install --upgrade pip
    call conda run -n MintaiDialect pip install -r backend\requirements.txt
) else (
    pip install --upgrade pip
    pip install -r backend\requirements.txt
)

REM 检查安装结果
echo 🔍 验证关键依赖安装...
call conda run -n MintaiDialect python -c "import fastapi; print('✅ FastAPI已安装')" 2>nul
if errorlevel 1 (
    echo ❌ FastAPI安装失败，尝试重新安装...
    call conda run -n MintaiDialect pip install fastapi uvicorn
)

call conda run -n MintaiDialect python -c "import uvicorn; print('✅ Uvicorn已安装')" 2>nul
if errorlevel 1 (
    echo ❌ Uvicorn安装失败，尝试重新安装...
    call conda run -n MintaiDialect pip install uvicorn[standard]
)

echo ✅ Python依赖安装完成

echo.
echo 📦 安装Node.js依赖...
cd frontend
call npm install
cd ..

echo.
echo 🤖 检查AI模型文件...
if not exist "backend\models\*" (
    echo ⚠️  模型目录为空，请下载必要的AI模型文件
    echo    建议下载以下模型：
    echo    - Whisper语音识别模型
    echo    - 闽台方言语音合成模型
    echo    - 翻译模型
)

echo.
echo ⚙️  创建环境配置...
if not exist "backend\.env" (
    (
        echo # 闽台方言大模型环境配置
        echo DATABASE_URL=sqlite:///./dialect_ai.db
        echo DEBUG=false
        echo LOG_LEVEL=INFO
        echo SECRET_KEY=your-secret-key-here
        echo API_KEY=your-api-key-here
        echo.
        echo # 模型路径配置
        echo MODEL_PATH=./models
        echo UPLOAD_PATH=./uploads
        echo LOG_PATH=./logs
        echo.
        echo # 服务配置
        echo HOST=0.0.0.0
        echo PORT=8000
        echo CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]
    ) > "backend\.env"
    echo ✅ 创建环境配置文件：backend\.env
)

echo.
echo 📝 启动脚本说明...
echo - 请确保 scripts\start.bat 文件存在
echo - 如需重新创建启动脚本，请手动编辑或复制
echo - 启动脚本应包含本地启动和Docker启动选项

echo.
echo 🎉 安装完成！
echo ===============================================
echo 📋 下一步操作：
echo 1. 启动服务：scripts\start.bat
echo 2. 或使用Docker：scripts\start-docker.bat
echo 3. 访问前端：http://localhost:3000
echo 4. 查看API文档：http://localhost:8000/docs

echo.
echo 💡 提示：
echo - 已创建并配置MintaiDialect conda环境
echo - 所有Python依赖已安装在MintaiDialect环境中
echo - 首次运行可能需要下载AI模型文件
echo - 建议使用Docker方式部署以获得最佳兼容性
echo - 如遇问题，请查看logs目录下的日志文件
echo.
echo 🔧 环境管理命令：
echo - 激活环境：conda activate MintaiDialect
echo - 查看环境：conda env list
echo - 更新依赖：conda run -n MintaiDialect pip install -r backend\requirements.txt

echo.
pause
