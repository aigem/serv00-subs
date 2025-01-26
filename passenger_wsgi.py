import os
import sys
from pathlib import Path

# 获取项目根目录
PROJECT_DIR = Path(__file__).parent
VENV_PATH = PROJECT_DIR / 'venv'

# 设置 VIRTUAL_ENV 环境变量
os.environ['VIRTUAL_ENV'] = str(VENV_PATH)

# 设置 Linux/Unix 路径（使用确切的 Python 版本）
site_packages = VENV_PATH / 'lib' / 'python3.11' / 'site-packages'
scripts_path = VENV_PATH / 'bin'

# 将虚拟环境的 bin 目录添加到 PATH
os.environ['PATH'] = str(scripts_path) + os.pathsep + os.environ['PATH']

# 添加虚拟环境的 site-packages 到 sys.path
if str(site_packages) not in sys.path:
    sys.path.insert(0, str(site_packages))

# 将应用的路径添加到 sys.path 中
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# 打印调试信息到日志
import logging
logging.basicConfig(filename='/tmp/passenger_wsgi.log', level=logging.DEBUG)
logging.debug(f"Python Version: {sys.version}")
logging.debug(f"Project Directory: {PROJECT_DIR}")
logging.debug(f"Virtual Env Path: {VENV_PATH}")
logging.debug(f"Site Packages: {site_packages}")
logging.debug(f"Scripts Path: {scripts_path}")
logging.debug(f"sys.path: {sys.path}")
logging.debug(f"PATH: {os.environ['PATH']}")

# 验证 site-packages 目录是否存在
if not site_packages.exists():
    logging.error(f"Site packages directory does not exist: {site_packages}")
    raise RuntimeError(f"Site packages directory not found: {site_packages}")

# 设置生产环境标志
os.environ['FLASK_ENV'] = 'production'

# 导入 Flask app 实例
from src.app import app as application

# Passenger 会直接使用 application 变量
