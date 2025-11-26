#!/bin/bash
# 一键停止 MintaiDialect 所有服务，稳健版本

PORTS=(8000 8008 9010 9011 9020 9030 9031 9032 5173 5174 7890)
LOG_DIR=${LOG_DIR:-~/MintaiDialect/mintai-logs}
RETRY=${RETRY:-5}
SLEEP_SEC=${SLEEP_SEC:-1}

echo "⏹ 正在停止 MintaiDialect 相关服务..."
echo "📋 目标端口: ${PORTS[*]}"
echo "---"

stopped_count=0

for port in "${PORTS[@]}"; do
    # 获取端口上的所有 PID（包含子进程）
    pid_list=$(lsof -ti tcp:$port 2>/dev/null || true)

    if [ -n "$pid_list" ]; then
        echo "⚠️  停止端口 $port 的进程: $(echo $pid_list | tr '\n' ' ')"
        # 强制杀掉所有 PID，允许 kill 失败
        kill -9 $pid_list 2>/dev/null || true

        # 等待端口释放
        for i in $(seq 1 $RETRY); do
            lsof -ti tcp:$port >/dev/null 2>&1
            if [ $? -ne 0 ]; then
                break
            fi
            sleep $SLEEP_SEC
        done

        # 再次检查端口是否还有进程
        remaining=$(lsof -ti tcp:$port 2>/dev/null || true)
        if [ -z "$remaining" ]; then
            echo "✅ 端口 $port 已完全停止"
        else
            echo "⚠️ 端口 $port 仍有进程: $remaining"
        fi
        ((stopped_count++))
    else
        echo "ℹ️  端口 $port 没有进程运行"
    fi
done

echo "---"
echo "🎉 停止完成! 共尝试停止 $stopped_count 个端口服务"
echo "📁 日志文件保存在: $LOG_DIR"
echo "🔄 重新启动: ./start-all.sh"
