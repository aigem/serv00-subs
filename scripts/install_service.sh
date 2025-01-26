#!/bin/bash
set -e  # 遇到错误立即退出

# 获取脚本所在目录的上级目录（项目根目录）
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 检查必要文件
for file in "requirements.txt" ".env.example"; do
    if [ ! -f "$PROJECT_DIR/$file" ]; then
        echo "错误：未找到 $file 文件"
        exit 1
    fi
done

# 创建并检查 .env 文件
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "已从 .env.example 创建 .env 文件"
fi

# 加载环境变量
set -a  # 自动导出所有变量
source "$PROJECT_DIR/.env"
set +a

# 使用配置值（添加默认值）
LOG_DIR=${LOG_DIR:-"/var/log/ytdlp"}
MONITOR_INTERVAL=${MONITOR_INTERVAL:-300}
SUBTITLE_DIR=${SUBTITLE_DIR:-"subtitles"}
TEMP_DIR=${TEMP_DIR:-"temp"}
API_PORT=${API_PORT:-5000}
API_HOST=${API_HOST:-"0.0.0.0"}

# 检查Python版本
python_version=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "当前 Python 版本: $python_version"

# 将版本号转换为整数进行比较（例如：3.8 -> 308）
version_num=$(echo "$python_version" | awk -F. '{ printf "%d%02d\n", $1, $2 }')
if [ "$version_num" -lt 308 ]; then
    echo "错误: 需要Python 3.8或更高版本"
    exit 1
fi

# 检查FFmpeg
if ! command -v ${FFMPEG_PATH:-"ffmpeg"} &> /dev/null; then
    echo "错误: 未安装FFmpeg"
    echo "请安装FFmpeg:"
    echo "Ubuntu/Debian: sudo apt install ffmpeg"
    echo "CentOS/RHEL: sudo yum install ffmpeg"
    exit 1
fi

# 检查并创建目录
create_dir() {
    local dir=$1
    local sudo_flag=$2
    
    if [ "$sudo_flag" = "sudo" ]; then
        sudo mkdir -p "$dir"
        sudo chown -R $USER:$USER "$dir"
    else
        mkdir -p "$dir"
    fi
    
    if [ ! -w "$dir" ]; then
        echo "错误：没有 $dir 的写入权限"
        exit 1
    fi
}

# 创建必要目录
create_dir "$LOG_DIR" "sudo"
create_dir "$PROJECT_DIR/$SUBTITLE_DIR"
create_dir "$PROJECT_DIR/$TEMP_DIR"

# 设置脚本权限
chmod +x "$PROJECT_DIR/scripts/"*.sh

# 配置日志轮转
sudo tee /etc/logrotate.d/ytdlp > /dev/null << EOL
$LOG_DIR/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 $USER $USER
}
EOL

# 添加 crontab 条目（使用配置的监控间隔）
(crontab -l 2>/dev/null | grep -v "ytdlp-serv00-subs") || true > /tmp/current_cron
cat << EOL >> /tmp/current_cron
# YouTube字幕下载服务监控
@reboot $PROJECT_DIR/scripts/start_service.sh
*/$((MONITOR_INTERVAL/60)) * * * * $PROJECT_DIR/scripts/monitor_service.sh
EOL
crontab /tmp/current_cron
rm /tmp/current_cron

# 创建并配置虚拟环境
if [ ! -d "$PROJECT_DIR/venv" ]; then
    python3 -m venv "$PROJECT_DIR/venv"
    source "$PROJECT_DIR/venv/bin/activate"
    pip install -r "$PROJECT_DIR/requirements.txt"
else
    source "$PROJECT_DIR/venv/bin/activate"
fi

# 显示配置摘要
echo "=== 安装配置摘要 ==="
echo "- Python版本: $python_version"
echo "- 日志目录: $LOG_DIR"
echo "- 监控间隔: $MONITOR_INTERVAL 秒"
echo "- API地址: $API_HOST:$API_PORT"
echo "- 字幕目录: $PROJECT_DIR/$SUBTITLE_DIR"
echo "- 临时目录: $PROJECT_DIR/$TEMP_DIR"
echo "===================="

# 启动服务
echo "正在启动服务..."
if "${PROJECT_DIR}/scripts/start_service.sh"; then
    echo "服务启动成功"
    echo "健康检查URL: http://${API_HOST}:${API_PORT}/health"
else
    echo "警告: 服务启动失败，请检查日志 $LOG_DIR/service.log"
    exit 1
fi 