#!/usr/bin/env python3
"""
版本映射管理工具
支持查看、添加、删除版本映射，以及从JIRA同步版本列表
"""

import asyncio
import sys
import os
import argparse
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Settings
from config.logger import get_logger
from services.jira_client import JiraClient
from services.version_mapper import VersionMapper


class VersionMappingManager:
    """版本映射管理器"""
    
    def __init__(self):
        self.settings = Settings()
        self.logger = get_logger("version_mapping_manager")
        self.jira_client = None
        self.version_mapper = None
    
    async def initialize(self):
        """初始化客户端"""
        try:
            # 初始化JIRA客户端
            self.jira_client = JiraClient(self.settings)
            await self.jira_client.initialize()
            
            # 初始化版本映射器
            self.version_mapper = VersionMapper(self.settings)
            
            print("✅ 初始化完成")
            
        except Exception as e:
            print(f"❌ 初始化失败: {str(e)}")
            raise
    
    async def cleanup(self):
        """清理资源"""
        if self.jira_client:
            await self.jira_client.close()
    
    async def show_status(self):
        """显示版本映射状态"""
        try:
            print("\n=== 版本映射状态 ===")
            
            status = await self.version_mapper.get_mapping_status()
            
            print(f"配置文件: {status.get('mapping_file')}")
            print(f"最后更新: {status.get('last_updated')}")
            print(f"JIRA同步时间: {status.get('jira_sync_time', '未同步')}")
            print(f"默认版本ID: {status.get('default_version_id')}")
            print(f"JIRA版本总数: {status.get('total_jira_versions')}")
            print(f"已映射版本数: {status.get('mapped_jira_versions')}")
            print(f"Notion版本名称总数: {status.get('total_notion_names')}")
            
            # 显示版本映射表
            version_mappings = status.get('version_mappings', {})
            if version_mappings:
                print("\n=== 版本映射表 ===")
                print(f"{'JIRA版本ID':<12} {'JIRA版本名称':<25} {'状态':<8} {'Notion版本名称'}")
                print("-" * 80)
                
                for version_id, mapping_info in version_mappings.items():
                    jira_name = mapping_info.get('jira_name', '')
                    notion_names = mapping_info.get('notion_names', [])
                    
                    # 状态标识
                    status_flags = []
                    if mapping_info.get('released'):
                        status_flags.append('已发布')
                    if mapping_info.get('archived'):
                        status_flags.append('已归档')
                    status_text = ','.join(status_flags) if status_flags else '活跃'
                    
                    # 显示映射信息
                    if notion_names:
                        for i, notion_name in enumerate(notion_names):
                            if i == 0:
                                print(f"{version_id:<12} {jira_name:<25} {status_text:<8} {notion_name}")
                            else:
                                print(f"{'':<12} {'':<25} {'':<8} {notion_name}")
                    else:
                        print(f"{version_id:<12} {jira_name:<25} {status_text:<8} [未映射]")
                    
                    # 显示备注
                    comment = mapping_info.get('comment', '')
                    if comment:
                        print(f"{'':<12} {'':<25} {'':<8} 备注: {comment}")
            
        except Exception as e:
            print(f"❌ 获取状态失败: {str(e)}")
    
    async def sync_jira_versions(self):
        """从JIRA同步版本列表"""
        try:
            print("\n=== 从JIRA同步版本列表 ===")
            
            success = await self.version_mapper.update_jira_versions(self.jira_client)
            
            if success:
                print("✅ JIRA版本列表同步成功")
                await self.show_status()
            else:
                print("❌ JIRA版本列表同步失败")
                
        except Exception as e:
            print(f"❌ 同步失败: {str(e)}")
    
    async def add_mapping(self, notion_version: str, jira_version_id: str):
        """添加版本映射"""
        try:
            print(f"\n=== 添加版本映射 ===")
            print(f"Notion版本: {notion_version}")
            print(f"JIRA版本ID: {jira_version_id}")
            
            # 验证JIRA版本ID是否存在
            status = await self.version_mapper.get_mapping_status()
            jira_versions = status.get('jira_versions', {})
            
            if jira_version_id not in jira_versions:
                print(f"⚠️  警告: JIRA版本ID '{jira_version_id}' 不在已知版本列表中")
                print("建议先运行 'sync' 命令同步JIRA版本列表")
                
                confirm = input("是否继续添加? (y/N): ").strip().lower()
                if confirm != 'y':
                    print("操作已取消")
                    return
            else:
                version_info = jira_versions[jira_version_id]
                print(f"JIRA版本名称: {version_info.get('name')}")
            
            success = await self.version_mapper.add_version_mapping(notion_version, jira_version_id)
            
            if success:
                print("✅ 版本映射添加成功")
            else:
                print("❌ 版本映射添加失败")
                
        except Exception as e:
            print(f"❌ 添加映射失败: {str(e)}")
    
    async def remove_mapping(self, notion_version: str):
        """移除版本映射"""
        try:
            print(f"\n=== 移除版本映射 ===")
            print(f"Notion版本: {notion_version}")
            
            success = await self.version_mapper.remove_version_mapping(notion_version)
            
            if success:
                print("✅ 版本映射移除成功")
            else:
                print("❌ 版本映射移除失败")
                
        except Exception as e:
            print(f"❌ 移除映射失败: {str(e)}")
    
    async def interactive_mode(self):
        """交互式模式"""
        print("\n=== 版本映射管理 - 交互式模式 ===")
        print("可用命令:")
        print("  status  - 显示当前状态")
        print("  sync    - 从JIRA同步版本列表")
        print("  add     - 添加版本映射")
        print("  remove  - 移除版本映射")
        print("  quit    - 退出")
        
        while True:
            try:
                command = input("\n请输入命令: ").strip().lower()
                
                if command == 'quit' or command == 'q':
                    break
                elif command == 'status':
                    await self.show_status()
                elif command == 'sync':
                    await self.sync_jira_versions()
                elif command == 'add':
                    notion_version = input("请输入Notion版本名称: ").strip()
                    if not notion_version:
                        print("版本名称不能为空")
                        continue
                    
                    jira_version_id = input("请输入JIRA版本ID: ").strip()
                    if not jira_version_id:
                        print("版本ID不能为空")
                        continue
                    
                    await self.add_mapping(notion_version, jira_version_id)
                elif command == 'remove':
                    notion_version = input("请输入要移除的Notion版本名称: ").strip()
                    if not notion_version:
                        print("版本名称不能为空")
                        continue
                    
                    await self.remove_mapping(notion_version)
                else:
                    print("未知命令，请重新输入")
                    
            except KeyboardInterrupt:
                print("\n\n操作已取消")
                break
            except Exception as e:
                print(f"❌ 执行命令失败: {str(e)}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="版本映射管理工具")
    parser.add_argument('command', nargs='?', choices=['status', 'sync', 'add', 'remove', 'interactive'], 
                       help='要执行的命令')
    parser.add_argument('--notion-version', help='Notion版本名称（用于add/remove命令）')
    parser.add_argument('--jira-version-id', help='JIRA版本ID（用于add命令）')
    
    args = parser.parse_args()
    
    manager = VersionMappingManager()
    
    try:
        await manager.initialize()
        
        if not args.command or args.command == 'interactive':
            await manager.interactive_mode()
        elif args.command == 'status':
            await manager.show_status()
        elif args.command == 'sync':
            await manager.sync_jira_versions()
        elif args.command == 'add':
            if not args.notion_version or not args.jira_version_id:
                print("❌ add命令需要 --notion-version 和 --jira-version-id 参数")
                return 1
            await manager.add_mapping(args.notion_version, args.jira_version_id)
        elif args.command == 'remove':
            if not args.notion_version:
                print("❌ remove命令需要 --notion-version 参数")
                return 1
            await manager.remove_mapping(args.notion_version)
        
        return 0
        
    except Exception as e:
        print(f"❌ 程序执行失败: {str(e)}")
        return 1
    finally:
        await manager.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 