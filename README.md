# YouTube字幕批量下载服务

一个高效的YouTube视频字幕批量下载和格式转换服务。支持并发下载、格式转换等特性。

## 功能特性

- 🚀 **批量处理**: 支持多个YouTube URL并发下载字幕
- 🔄 **格式转换**: 支持将SRT字幕转换为TXT、JSON格式
- 💾 **本地缓存**: 内置简单缓存，提高重复URL处理速度
- 🧹 **自动清理**: 定期清理过期文件，无需手动维护
- 🛡️ **错误处理**: 完善的错误处理和重试机制
- 🔄 **自动监控**: 服务状态监控和自动恢复

## 系统要求

- Python 3.8+
- FFmpeg（用于格式转换）
- 至少100MB可用磁盘空间
- Linux系统（已在Ubuntu 20.04+测试）
- sudo权限（用于日志目录创建）

## 安装步骤

1. **克隆仓库**
```bash
git clone <repository-url>
cd ytdlp-serv00-subs
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **安装FFmpeg**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg
```

5. **配置环境变量**
```bash
cp .env.example .env
# 根据需要编辑.env文件
```

6. **安装服务**
```bash
# 设置脚本权限并运行安装脚本
chmod +x scripts/install_service.sh
./scripts/install_service.sh
```

## 配置说明

编辑`.env`文件，配置以下参数：

```ini
# API配置
API_HOST=0.0.0.0        # API监听地址
API_PORT=5000           # API监听端口
API_WORKERS=4           # 工作进程数

# 性能配置
MAX_CONCURRENT=8        # 最大并发下载数（建议不超过CPU核心数的2倍）
CLEANUP_INTERVAL=3600   # 清理间隔(秒)
FILE_RETENTION_HOURS=24 # 文件保留时间(小时)

# FFmpeg配置
FFMPEG_PATH=ffmpeg      # FFmpeg可执行文件路径
```

## 服务管理

### 1. 服务状态检查
```bash
# 查看服务状态
curl http://localhost:5000/health

# 查看监控日志
tail -f /var/log/ytdlp/monitor.log

# 查看服务日志
tail -f /var/log/ytdlp/service.log
```

### 2. 服务控制
```bash
# 手动启动服务
./scripts/start_service.sh

# 停止服务
pkill -f "python.*src.run"

# 重启服务
./scripts/monitor_service.sh
```

### 3. 自动监控说明

- **监控频率**: 每5分钟自动检查服务状态
- **健康检查**: 通过HTTP接口验证服务是否正常响应
- **自动恢复**: 发现服务异常时自动重启
- **开机自启**: 系统重启后自动启动服务

### 4. 日志管理
```bash
# 日志位置
/var/log/ytdlp/
├── monitor.log  # 监控脚本日志
└── service.log  # 服务运行日志

# 日志自动轮转
- 每日轮转
- 保留7天
- 自动压缩
```

## API使用说明

### 1. 健康检查
```bash
curl http://localhost:5000/health
```

### 2. 下载字幕
```bash
curl -X POST http://localhost:5000/batch_subs \
-H "Content-Type: application/json" \
-d '{
    "urls": [
        "https://youtu.be/video1",
        "https://youtu.be/video2"
    ],
    "lang": "en",
    "convert": "txt"
}'
```

#### 请求参数说明

- `urls`: YouTube视频URL列表或单个URL（必填）
- `lang`: 字幕语言代码（可选，默认: "en"）
- `convert`: 转换格式（可选: "txt"/"json"）

#### 功能限制

- 单次请求最多处理50个URL
- 支持的字幕语言: en, zh, ja, ko, es, fr, de
- 字幕文件大小限制: 10MB
- URL必须是有效的YouTube视频链接

#### 响应示例

```json
{
    "status": "success",
    "results": [
        {
            "status": "success",
            "url": "https://youtu.be/video1",
            "video_id": "video1",
            "path": "/path/to/subtitle.srt",
            "content": "字幕内容...",
            "converted_path": "/path/to/subtitle.txt",
            "converted_content": "转换后的内容..."
        }
    ]
}
```

## 故障排除

### 1. 服务启动失败
```bash
# 检查服务状态
./scripts/monitor_service.sh

# 查看详细错误日志
tail -f /var/log/ytdlp/service.log
```

### 2. 监控不工作
```bash
# 检查crontab配置
crontab -l

# 检查监控日志
tail -f /var/log/ytdlp/monitor.log
```

### 3. 常见问题解决

- **多个服务实例**: 监控脚本会自动终止多余的实例
- **服务无响应**: 监控脚本会自动重启无响应的服务
- **日志写入失败**: 检查 `/var/log/ytdlp` 目录权限
- **FFmpeg相关问题**: 检查FFmpeg安装和路径配置
- **下载失败**: 检查网络连接和URL有效性

## 维护说明

### 1. 日常维护
- 监控脚本自动运行，无需手动干预
- 日志自动轮转，无需手动清理
- 临时文件自动清理（24小时后）

### 2. 建议检查项
- 定期查看监控日志了解服务状态
- 检查磁盘空间使用情况
- 确认crontab任务正常运行

### 3. 升级注意事项
- 升级前停止服务
- 备份配置文件
- 升级后重新运行安装脚本

## 版本信息

当前版本：1.1.0
- 支持YouTube字幕批量下载
- 支持SRT到TXT/JSON的转换
- 内置简单缓存和自动清理
- 服务监控和自动恢复
