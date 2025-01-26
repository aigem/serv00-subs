# YouTube字幕批量下载服务

一个高效的YouTube视频字幕批量下载和格式转换服务。支持并发下载、格式转换等特性。

## 功能特性

- 🚀 **批量处理**: 支持多个YouTube URL并发下载字幕-TTML格式
- 🔄 **格式转换**: 支持将TTML字幕转换为TXT、JSON格式
- 💾 **本地缓存**: 内置简单缓存，提高重复URL处理速度
- 🧹 **自动清理**: 定期清理过期文件，无需手动维护
- 🛡️ **错误处理**: 完善的错误处理和重试机制
- 🔄 **API路由**: 支持API路由，方便调用

## 系统要求

- Python 3.8+
- FFmpeg（用于格式转换）
- 至少100MB可用磁盘空间
- Linux系统


## serv00中 python app方式的安装步骤：
先在serv00中创建一个python app，然后按照以下步骤进行安装：
0. 如何在serv00中创建一个website, 选择python app。
之后ssh登录到serv00，然后执行以下命令：

1. **克隆仓库**
```bash
cd /home/<你的用户名>/domains/<你的网站域名>
e.g. cd /home/gepi/domains/ytdlp.ydns.eu

git clone https://github.com/aigem/serv00-subs.git public_python
cd public_python
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

4. **配置环境变量**
```bash
cp .env.example .env
# 根据需要编辑.env文件
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

### 3. 直接运行的方式
如果您不想使用crontab进行服务管理，可以直接运行Python程序：

```bash
# 1. 激活虚拟环境
source venv/bin/activate  # Linux

# 2. 安装必要依赖
pip install -r requirements.txt

# 3. 直接运行程序
python -m src.run

注意事项：
- 直接运行时需要确保已正确配置`.env`文件
- 程序会自动处理日志记录和临时文件清理

### 4. 自动监控说明

- **健康检查**: 通过HTTP接口验证服务是否正常响应

### 5. 日志管理
```bash
# 日志位置
/程序文件夹下
logs/
└── service.log  # 服务运行日志
subtitles/
└── 字幕文件  # 字幕文件
temp/
└── 临时文件  # 临时文件，转换后的文件，定时清理

# 日志自动轮转
- 每日轮转
- 保留7天
```

## API使用说明

### 1. 健康检查
```bash
curl http://localhost:5000/health
```

### 2. 批量下载字幕 (带缓存和转换)
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
- `convert`: 转换格式（可选: "txt"/"json"/"none"）

#### 响应示例
```json
{
    "status": "success",
    "results": [
        {
            "status": "success",
            "url": "https://youtu.be/video1",
            "video_id": "video1",
            "path": "/path/to/subtitle.ttml",
            "content": "原始TTML内容",
            "converted_path": "/path/to/subtitle.txt",
            "converted_content": "转换后的内容",
            "type": "normal"  // 或 "auto" 表示自动生成的字幕
        }
    ]
}
```

### 3. 快速获取字幕文本 (适用于 n8n 集成)
```bash
curl -X POST http://localhost:5000/quick \
-H "Content-Type: application/json" \
-d '{
    "url": "https://youtu.be/video1",
    "lang": "en"
}'
```
#### 响应示例
```json
{
    "status": "success",
    "text": "字幕文本内容",
    "thumbnail": "视频缩略图URL",
    "title": "视频标题"
}
```

#### 请求参数说明
- `url`: YouTube视频URL（必填）
- `lang`: 字幕语言代码（可选，默认: "en"）

#### 响应示例
```json
{
    "status": "success",
    "text": "字幕文本内容",
    "thumbnail": "视频缩略图URL",
    "title": "视频标题"
}
```

#### 功能限制

- 批量API单次请求最多处理50个URL
- 支持的字幕语言: en, zh, ja, ko, es, fr, de
- 字幕文件大小限制: 10MB
- URL必须是有效的YouTube视频链接
- 字幕格式：
  - 下载格式：TTML
  - 转换格式：TXT, JSON
- 缓存时间：默认30分钟

#### API 特点说明

1. **批量下载API** (`/batch_subs`)
   - 支持多URL并发处理
   - 提供缓存机制
   - 支持格式转换
   - 保存文件到本地
   - 返回完整的处理信息

2. **快速API** (`/quick`)
   - 单URL快速处理
   - 直接返回文本内容
   - 包含视频元数据（标题、缩略图）
   - 不保存转换文件
   - 适合需要快速响应的场景

#### 使用建议

- 批量处理多个视频时使用 `/batch_subs`
- 需要快速获取单个视频字幕文本时使用 `/quick`
- 需要获取视频元数据时使用 `/quick`
- 需要保存文件到本地时使用 `/batch_subs`

### 3. 常见问题解决

- **多个服务实例**: 监控脚本会自动终止多余的实例
- **服务无响应**: 监控脚本会自动重启无响应的服务
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

## 版本信息

当前版本：1.2.0
- 支持YouTube字幕批量下载
- 支持TTML到TXT/JSON的转换
- 内置简单缓存和自动清理
- 支持API路由
