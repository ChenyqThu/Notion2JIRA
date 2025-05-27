#!/usr/bin/env python3
"""
Notion2JIRA 内网同步服务主程序
负责消费Redis队列中的同步任务，执行Notion和JIRA之间的数据同步
"""

import asyncio
import logging
import signal
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Settings
from config.logger import setup_logger
from services.redis_client import RedisClient
from services.sync_service import SyncService
from services.monitor_service import MonitorService


class SyncServiceApp:
    """内网同步服务应用主类"""
    
    def __init__(self):
        self.settings = Settings()
        self.logger = setup_logger()
        self.redis_client = None
        self.sync_service = None
        self.monitor_service = None
        self.running = False
        
    async def initialize(self):
        """初始化所有服务组件"""
        try:
            self.logger.info("正在初始化内网同步服务...")
            
            # 初始化Redis客户端
            self.redis_client = RedisClient(self.settings)
            await self.redis_client.connect()
            self.logger.info("Redis连接已建立")
            
            # 初始化同步服务
            self.sync_service = SyncService(self.settings, self.redis_client)
            await self.sync_service.initialize()
            self.logger.info("同步服务已初始化")
            
            # 初始化监控服务
            self.monitor_service = MonitorService(self.settings, self.redis_client)
            await self.monitor_service.initialize()
            self.logger.info("监控服务已初始化")
            
            self.logger.info("内网同步服务初始化完成")
            
        except Exception as e:
            self.logger.error(f"服务初始化失败: {e}")
            raise
    
    async def start(self):
        """启动同步服务"""
        try:
            await self.initialize()
            
            self.running = True
            self.logger.info("内网同步服务启动成功")
            
            # 启动各个服务组件
            tasks = [
                asyncio.create_task(self.sync_service.start_consumer(), name="sync_consumer"),
                asyncio.create_task(self.monitor_service.start_monitoring(), name="monitor"),
                asyncio.create_task(self._health_check_loop(), name="health_check")
            ]
            
            # 等待所有任务完成或出错
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            self.logger.error(f"服务启动失败: {e}")
            raise
    
    async def stop(self):
        """停止同步服务"""
        self.logger.info("正在停止内网同步服务...")
        self.running = False
        
        try:
            # 停止各个服务组件
            if self.sync_service:
                await self.sync_service.stop()
                
            if self.monitor_service:
                await self.monitor_service.stop()
                
            # 关闭Redis连接
            if self.redis_client:
                await self.redis_client.disconnect()
                
            self.logger.info("内网同步服务已停止")
            
        except Exception as e:
            self.logger.error(f"服务停止过程中发生错误: {e}")
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while self.running:
            try:
                # 检查Redis连接
                redis_status = await self.redis_client.ping()
                
                # 检查同步服务状态
                sync_status = self.sync_service.get_status() if self.sync_service else False
                
                # 记录健康状态
                if redis_status and sync_status:
                    self.logger.debug("服务健康检查通过")
                else:
                    self.logger.warning(f"服务健康检查异常: Redis={redis_status}, Sync={sync_status}")
                
                # 等待下次检查
                await asyncio.sleep(30)  # 30秒检查一次
                
            except Exception as e:
                self.logger.error(f"健康检查失败: {e}")
                await asyncio.sleep(10)  # 出错时缩短检查间隔


def setup_signal_handlers(app: SyncServiceApp):
    """设置信号处理器，用于优雅关闭"""
    
    def signal_handler(signum, frame):
        """信号处理函数"""
        signal_name = signal.Signals(signum).name
        logging.getLogger().info(f"收到信号 {signal_name}，开始优雅关闭...")
        
        # 创建停止任务
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(app.stop())
        else:
            asyncio.run(app.stop())
        
        sys.exit(0)
    
    # 注册信号处理器
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


async def main():
    """主函数"""
    app = SyncServiceApp()
    
    try:
        # 设置信号处理器
        setup_signal_handlers(app)
        
        # 启动服务
        await app.start()
        
    except KeyboardInterrupt:
        app.logger.info("收到键盘中断信号")
    except Exception as e:
        app.logger.error(f"服务运行异常: {e}")
        return 1
    finally:
        await app.stop()
    
    return 0


if __name__ == "__main__":
    # 设置事件循环策略（Linux环境优化）
    if sys.platform.startswith('linux'):
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    
    # 运行主程序
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 