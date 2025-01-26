#!/usr/bin/env python3
import os
import sys
import subprocess
import logging
from pathlib import Path
import requests
import time
from .config import config  # 修改导入

# 修改日志配置
log_file = config.LOG_DIR / 'monitor.log'

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

def is_service_running():
    """检查服务是否运行，更精确的进程检查"""
    try:
        # 使用更精确的进程匹配
        result = subprocess.run(
            ['pgrep', '-f', 'python.*src.run'],
            capture_output=True,
            text=True
        )
        processes = result.stdout.strip().split('\n')
        # 过滤掉空字符串
        processes = [p for p in processes if p]
        
        if not processes:
            return False
            
        if len(processes) > 1:
            logging.warning(f"检测到多个服务进程: {processes}")
            # 可以选择保留最早的进程，终止其他进程
            for pid in processes[1:]:
                try:
                    subprocess.run(['kill', pid], check=True)
                    logging.info(f"终止重复的进程: {pid}")
                except subprocess.CalledProcessError:
                    logging.error(f"终止进程失败: {pid}")
                    
        return True
    except Exception as e:
        logging.error(f"检查服务状态失败: {e}")
        return False

def stop_service():
    """停止服务"""
    try:
        subprocess.run(
            ['pkill', '-f', 'python.*src.run'],
            check=True
        )
        logging.info("服务已停止")
        return True
    except subprocess.CalledProcessError:
        logging.error("停止服务失败")
        return False

def start_service():
    """启动服务前先检查"""
    if is_service_running():
        logging.info("服务已在运行")
        return True
        
    try:
        # 获取脚本所在目录的上级目录（项目根目录）
        project_dir = Path(__file__).parent.parent
        
        # 设置工作目录和环境变量
        env = os.environ.copy()
        env['PRODUCTION'] = 'true'
        
        # 启动服务
        subprocess.Popen(
            ['python', '-m', 'src.run'],
            cwd=str(project_dir),
            env=env,
            stdout=open('/var/log/ytdlp/service.log', 'a'),
            stderr=subprocess.STDOUT
        )
        logging.info("服务已启动")
        
        # 等待服务启动
        time.sleep(2)
        if check_service_health():
            logging.info("服务启动成功并响应正常")
            return True
        else:
            logging.error("服务启动后健康检查失败")
            return False
            
    except Exception as e:
        logging.error(f"启动服务失败: {e}")
        return False

def check_service_health():
    """检查服务健康状态"""
    try:
        response = requests.get(config.HEALTH_CHECK_URL)
        return response.status_code == 200
    except:
        return False

def main():
    """主函数"""
    if not is_service_running():
        logging.info("服务未运行，正在启动...")
        if not start_service():
            logging.error("服务启动失败")
            sys.exit(1)
    elif not check_service_health():
        logging.warning("服务运行但响应异常，正在重启...")
        if stop_service():
            time.sleep(1)  # 等待进程完全停止
            if not start_service():
                logging.error("服务重启失败")
                sys.exit(1)
        else:
            logging.error("服务停止失败")
            sys.exit(1)
    else:
        logging.info("服务运行正常")

if __name__ == '__main__':
    main() 