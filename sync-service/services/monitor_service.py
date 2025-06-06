"""
监控服务模块
负责监控系统状态、性能指标和健康检查
"""

import asyncio
import time
import psutil
from typing import Dict, Any, Optional
from datetime import datetime

from config.settings import Settings
from config.logger import get_logger
from services.redis_client import RedisClient


class MonitorService:
    """监控服务类"""
    
    def __init__(self, settings: Settings, redis_client: RedisClient):
        self.settings = settings
        self.redis_client = redis_client
        self.logger = get_logger("monitor_service")
        self.running = False
        self.monitor_task = None
        
        # 监控数据
        self.metrics = {
            "start_time": None,
            "last_check": None,
            "system_info": {},
            "performance_history": []
        }
    
    async def initialize(self):
        """初始化监控服务"""
        try:
            self.logger.info("正在初始化监控服务...")
            
            # 收集系统基础信息
            self.metrics["system_info"] = self._get_system_info()
            self.metrics["start_time"] = time.time()
            
            self.logger.info("监控服务初始化完成")
            
        except Exception as e:
            self.logger.error("监控服务初始化失败", error=str(e))
            raise
    
    async def start_monitoring(self):
        """启动监控循环"""
        self.running = True
        self.logger.info("启动系统监控")
        
        while self.running:
            try:
                await self._collect_metrics()
                await asyncio.sleep(60)  # 每分钟收集一次指标
                
            except Exception as e:
                self.logger.error("监控数据收集失败", error=str(e))
                await asyncio.sleep(30)  # 出错时缩短间隔
    
    async def stop(self):
        """停止监控服务"""
        self.logger.info("正在停止监控服务...")
        self.running = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("监控服务已停止")
    
    async def _collect_metrics(self):
        """收集系统指标"""
        try:
            current_time = time.time()
            
            # 收集系统性能指标
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 收集Redis指标
            redis_stats = await self.redis_client.get_stats()
            
            # 构建指标数据
            metrics = {
                "timestamp": current_time,
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_used_gb": round(memory.used / (1024**3), 2),
                    "memory_total_gb": round(memory.total / (1024**3), 2),
                    "disk_percent": disk.percent,
                    "disk_used_gb": round(disk.used / (1024**3), 2),
                    "disk_total_gb": round(disk.total / (1024**3), 2)
                },
                "redis": redis_stats,
                "uptime": current_time - self.metrics["start_time"]
            }
            
            # 保存到历史记录（保留最近100条）
            self.metrics["performance_history"].append(metrics)
            if len(self.metrics["performance_history"]) > 100:
                self.metrics["performance_history"].pop(0)
            
            self.metrics["last_check"] = current_time
            
            # 检查告警条件
            await self._check_alerts(metrics)
            
            self.logger.debug(
                "系统指标收集完成",
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                redis_connected=redis_stats.get("connected", False)
            )
            
        except Exception as e:
            self.logger.error("收集系统指标失败", error=str(e))
    
    async def _check_alerts(self, metrics: Dict[str, Any]):
        """检查告警条件"""
        try:
            alerts = []
            
            # CPU使用率告警
            cpu_percent = metrics["system"]["cpu_percent"]
            if cpu_percent > 80:
                alerts.append({
                    "type": "high_cpu",
                    "level": "warning" if cpu_percent < 90 else "critical",
                    "message": f"CPU使用率过高: {cpu_percent}%",
                    "value": cpu_percent
                })
            
            # 内存使用率告警 - 阈值提升到90%
            memory_percent = metrics["system"]["memory_percent"]
            if memory_percent > 90:
                alerts.append({
                    "type": "high_memory",
                    "level": "warning" if memory_percent < 95 else "critical",
                    "message": f"内存使用率过高: {memory_percent}%",
                    "value": memory_percent
                })
            
            # 磁盘使用率告警
            disk_percent = metrics["system"]["disk_percent"]
            if disk_percent > 85:
                alerts.append({
                    "type": "high_disk",
                    "level": "warning" if disk_percent < 95 else "critical",
                    "message": f"磁盘使用率过高: {disk_percent}%",
                    "value": disk_percent
                })
            
            # Redis连接告警
            if not metrics["redis"].get("connected", False):
                alerts.append({
                    "type": "redis_disconnected",
                    "level": "critical",
                    "message": "Redis连接断开",
                    "value": False
                })
            
            # 队列积压告警
            queue_length = metrics["redis"].get("queue_length", 0)
            if queue_length > 100:
                alerts.append({
                    "type": "queue_backlog",
                    "level": "warning" if queue_length < 500 else "critical",
                    "message": f"队列积压严重: {queue_length}条消息",
                    "value": queue_length
                })
            
            # 记录告警
            for alert in alerts:
                if alert["level"] == "critical":
                    self.logger.error(alert["message"], alert_type=alert["type"], value=alert["value"])
                else:
                    self.logger.warning(alert["message"], alert_type=alert["type"], value=alert["value"])
            
        except Exception as e:
            self.logger.error("检查告警条件失败", error=str(e))
    
    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统基础信息"""
        try:
            return {
                "platform": psutil.LINUX if hasattr(psutil, 'LINUX') else "unknown",
                "cpu_count": psutil.cpu_count(),
                "cpu_count_logical": psutil.cpu_count(logical=True),
                "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "disk_total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
                "python_version": f"{psutil.version_info}",
                "boot_time": psutil.boot_time()
            }
        except Exception as e:
            self.logger.error("获取系统信息失败", error=str(e))
            return {}
    
    def get_current_status(self) -> Dict[str, Any]:
        """获取当前系统状态"""
        try:
            current_time = time.time()
            
            # 获取最新的性能数据
            latest_metrics = self.metrics["performance_history"][-1] if self.metrics["performance_history"] else {}
            
            return {
                "running": self.running,
                "uptime": current_time - self.metrics["start_time"] if self.metrics["start_time"] else 0,
                "last_check": self.metrics["last_check"],
                "last_check_ago": current_time - self.metrics["last_check"] if self.metrics["last_check"] else None,
                "system_info": self.metrics["system_info"],
                "current_metrics": latest_metrics,
                "metrics_count": len(self.metrics["performance_history"])
            }
            
        except Exception as e:
            self.logger.error("获取系统状态失败", error=str(e))
            return {"error": str(e)}
    
    def get_performance_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """获取性能摘要（最近N分钟）"""
        try:
            current_time = time.time()
            cutoff_time = current_time - (minutes * 60)
            
            # 筛选指定时间范围内的数据
            recent_metrics = [
                m for m in self.metrics["performance_history"]
                if m.get("timestamp", 0) >= cutoff_time
            ]
            
            if not recent_metrics:
                return {"message": "没有足够的历史数据"}
            
            # 计算平均值和最大值
            cpu_values = [m["system"]["cpu_percent"] for m in recent_metrics]
            memory_values = [m["system"]["memory_percent"] for m in recent_metrics]
            
            return {
                "time_range_minutes": minutes,
                "data_points": len(recent_metrics),
                "cpu": {
                    "avg": round(sum(cpu_values) / len(cpu_values), 2),
                    "max": max(cpu_values),
                    "min": min(cpu_values)
                },
                "memory": {
                    "avg": round(sum(memory_values) / len(memory_values), 2),
                    "max": max(memory_values),
                    "min": min(memory_values)
                },
                "redis_status": recent_metrics[-1]["redis"] if recent_metrics else {}
            }
            
        except Exception as e:
            self.logger.error("获取性能摘要失败", error=str(e))
            return {"error": str(e)}
    
    async def get_health_check(self) -> Dict[str, Any]:
        """执行健康检查"""
        try:
            current_time = time.time()
            health_status = "healthy"
            issues = []
            
            # 检查Redis连接
            redis_connected = await self.redis_client.ping()
            if not redis_connected:
                health_status = "unhealthy"
                issues.append("Redis连接失败")
            
            # 检查系统资源
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil.virtual_memory().percent
                disk_percent = psutil.disk_usage('/').percent
                
                if cpu_percent > 90:
                    health_status = "degraded" if health_status == "healthy" else health_status
                    issues.append(f"CPU使用率过高: {cpu_percent}%")
                
                if memory_percent > 95:
                    health_status = "degraded" if health_status == "healthy" else health_status
                    issues.append(f"内存使用率过高: {memory_percent}%")
                
                if disk_percent > 95:
                    health_status = "degraded" if health_status == "healthy" else health_status
                    issues.append(f"磁盘使用率过高: {disk_percent}%")
                    
            except Exception as e:
                health_status = "unhealthy"
                issues.append(f"系统资源检查失败: {str(e)}")
            
            # 检查服务运行时间
            uptime = current_time - self.metrics["start_time"] if self.metrics["start_time"] else 0
            
            return {
                "status": health_status,
                "timestamp": current_time,
                "uptime_seconds": uptime,
                "redis_connected": redis_connected,
                "issues": issues,
                "checks_performed": [
                    "redis_connection",
                    "system_resources",
                    "service_uptime"
                ]
            }
            
        except Exception as e:
            self.logger.error("健康检查失败", error=str(e))
            return {
                "status": "unhealthy",
                "timestamp": time.time(),
                "error": str(e)
            } 