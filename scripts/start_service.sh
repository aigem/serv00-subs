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

# 使用配置值（添加默认值）
LOG_DIR=${LOG_DIR:-"/var/log/ytdlp"}
API_HOST=${API_HOST:-"0.0.0.0"}
API_PORT=${API_PORT:-5000}
API_WORKERS=${API_WORKERS:-4}

# 确保日志目录存在
mkdir -p "$LOG_DIR"

# 激活虚拟环境
source "$PROJECT_DIR/venv/bin/activate"

# 设置环境变量
export PRODUCTION=true

# 启动服务（使用配置的 API 参数）
cd "$PROJECT_DIR"
echo "$(date): 启动服务 - HOST=$API_HOST PORT=$API_PORT WORKERS=$API_WORKERS" >> "$LOG_DIR/service.log"
python -m src.run >> "$LOG_DIR/service.log" 2>&1

# 添加在服务启动后
echo "等待服务启动..."
sleep 2
if curl -s "http://${API_HOST}:${API_PORT}/health" > /dev/null; then
    echo "服务启动成功"
else
    echo "警告：服务可能未正常启动，请检查日志"
    exit 1
fi 