import os
import sys
from pathlib import Path

# 获取项目根目录
PROJECT_DIR = Path(__file__).parent
VENV_PATH = PROJECT_DIR / 'venv'

# 设置 VIRTUAL_ENV 环境变量
os.environ['VIRTUAL_ENV'] = str(VENV_PATH)

# 将虚拟环境的 Scripts 目录添加到 PATH (Windows)
os.environ['PATH'] = str(VENV_PATH / 'Scripts') + os.pathsep + os.environ['PATH']

# 添加虚拟环境的 site-packages 到 sys.path
site_packages = VENV_PATH / 'Lib/site-packages'
sys.path.insert(0, str(site_packages))

# 将应用的路径添加到 sys.path 中
sys.path.append(str(PROJECT_DIR))

# 设置生产环境标志，但不使用 gunicorn
os.environ['PRODUCTION'] = 'true'
os.environ['FLASK_ENV'] = 'production'

# 导入 Flask app 实例
from src.app import app as application

# Passenger 会直接使用 application 变量
