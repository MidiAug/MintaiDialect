@echo off 
chcp 65001 >nul 
echo 🐍 正在启动后端服务... 
echo 🔧 激活MintaiDialect环境... 
call conda activate MintaiDialect 
echo ✅ 环境已激活，当前环境: %CONDA_DEFAULT_ENV% 
echo 🚀 启动后端服务... 
cd backend 
python -m app.main 
pause 
