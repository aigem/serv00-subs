#!/bin/bash
set -e  # 遇到错误立即退出

# 获取脚本所在目录的上级目录（项目根目录）
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 加载环境变量
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a  # 自动导出所有变量
    source "$PROJECT_DIR/.env"
    set +a
else
    echo "错误：未找到 .env 文件"
    exit 1
fi

# 使用配置值
LOG_DIR=${LOG_DIR:-"/var/log/ytdlp"}
MONITOR_INTERVAL=${MONITOR_INTERVAL:-300}

# 确保日志目录存在
mkdir -p "$LOG_DIR"

# 激活虚拟环境
source "$PROJECT_DIR/venv/bin/activate"

# 记录监控启动
echo "$(date): 开始监控检查 - 间隔=$MONITOR_INTERVAL秒" >> "$LOG_DIR/monitor.log"

# 验证监控配置
if [ "$MONITOR_INTERVAL" -lt 60 ]; then
    echo "警告：监控间隔太短（${MONITOR_INTERVAL}秒），可能影响性能"
fi

# 验证健康检查URL
if ! curl -s "$HEALTH_CHECK_URL" > /dev/null; then
    echo "警告：健康检查URL不可访问"
fi

# 运行监控脚本
python -m src.monitor 