#!/usr/bin/env python3
"""
配置初始化脚本
帮助用户创建和配置.env文件
"""

import os
import sys
from pathlib import Path


def create_env_file():
    """创建.env文件"""
    
    # 获取sync-service目录路径
    sync_service_dir = Path(__file__).parent.parent
    env_file_path = sync_service_dir / '.env'
    
    # .env文件内容模板
    env_template = """# ===========================================
# Notion2JIRA 同步服务环境配置
# ===========================================

# ============ 服务配置 ============
# 服务运行环境
ENVIRONMENT=development
# 日志级别
LOG_LEVEL=INFO
# 服务端口
SERVICE_PORT=8001

# ============ Redis 配置 ============
# Redis服务器地址
REDIS_HOST=localhost
# Redis服务器端口
REDIS_PORT=6379
# Redis数据库编号
REDIS_DB=0
# Redis密码（如果有）
REDIS_PASSWORD=
# Redis连接池大小
REDIS_POOL_SIZE=10

# ============ Notion 配置 ============
# Notion集成Token
NOTION_TOKEN=secret_your_notion_integration_token_here
# Notion数据库ID
NOTION_DATABASE_ID=your_notion_database_id_here
# Notion API版本
NOTION_API_VERSION=2022-06-28

# ============ JIRA 配置 ============
# JIRA服务器地址
JIRA_BASE_URL=http://rdjira.tp-link.com
# JIRA用户邮箱
JIRA_USER_EMAIL=your_email@tp-link.com
# JIRA用户密码或API Token
JIRA_USER_PASSWORD=your_password_here
# JIRA项目Key
JIRA_PROJECT_KEY=SMBNET
# JIRA默认Issue类型
JIRA_DEFAULT_ISSUE_TYPE=Story
# JIRA请求超时时间（秒）
JIRA_TIMEOUT=30
# 是否验证SSL证书（内网环境建议设为false）
JIRA_VERIFY_SSL=false

# ============ 同步配置 ============
# 同步间隔（秒）
SYNC_INTERVAL=300
# 批处理大小
BATCH_SIZE=10
# 最大重试次数
MAX_RETRY_COUNT=3
# 重试间隔（秒）
RETRY_INTERVAL=5

# ============ 调试配置 ============
# 是否启用调试模式
DEBUG=true
# 是否保存详细日志
VERBOSE_LOGGING=true
# 测试模式（不实际创建JIRA Issue）
TEST_MODE=false"""

    try:
        # 检查文件是否已存在
        if env_file_path.exists():
            response = input(f".env文件已存在于 {env_file_path}，是否覆盖？(y/N): ")
            if response.lower() != 'y':
                print("操作已取消")
                return False
        
        # 写入.env文件
        with open(env_file_path, 'w', encoding='utf-8') as f:
            f.write(env_template)
        
        print(f"✅ .env文件已创建: {env_file_path}")
        print("\n📝 请编辑.env文件，填入实际的配置值：")
        print("   - JIRA_USER_EMAIL: 你的JIRA邮箱")
        print("   - JIRA_USER_PASSWORD: 你的JIRA密码")
        print("   - NOTION_TOKEN: Notion集成Token（可选，用于反向同步）")
        print("   - NOTION_DATABASE_ID: Notion数据库ID（可选，用于反向同步）")
        print("\n💡 提示：")
        print("   - 敏感信息请妥善保管，不要提交到版本控制系统")
        print("   - Webhook配置属于webhook-server，不在此文件中")
        print("   - sync-service只需要Redis和JIRA配置即可运行")
        
        return True
        
    except Exception as e:
        print(f"❌ 创建.env文件失败: {e}")
        return False


def validate_env_file():
    """验证.env文件配置"""
    
    sync_service_dir = Path(__file__).parent.parent
    env_file_path = sync_service_dir / '.env'
    
    if not env_file_path.exists():
        print(f"❌ .env文件不存在: {env_file_path}")
        return False
    
    # 必需的配置项（sync-service核心功能）
    required_configs = [
        'JIRA_BASE_URL',
        'JIRA_USER_EMAIL', 
        'JIRA_USER_PASSWORD',
        'JIRA_PROJECT_KEY'
    ]
    
    # 可选的配置项（用于反向同步）
    optional_configs = [
        'NOTION_TOKEN',
        'NOTION_DATABASE_ID'
    ]
    
    # 读取.env文件
    env_vars = {}
    try:
        with open(env_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except Exception as e:
        print(f"❌ 读取.env文件失败: {e}")
        return False
    
    # 检查必需配置
    missing_configs = []
    placeholder_configs = []
    optional_missing = []
    
    for config in required_configs:
        if config not in env_vars:
            missing_configs.append(config)
        elif env_vars[config] in ['', 'your_email@tp-link.com', 'your_password_here']:
            placeholder_configs.append(config)
    
    # 检查可选配置
    for config in optional_configs:
        if config not in env_vars or env_vars[config] in ['', 'secret_your_notion_integration_token_here', 'your_notion_database_id_here']:
            optional_missing.append(config)
    
    # 输出验证结果
    if missing_configs:
        print(f"❌ 缺少必需配置: {', '.join(missing_configs)}")
    
    if placeholder_configs:
        print(f"⚠️  以下配置仍为占位符，需要填入实际值: {', '.join(placeholder_configs)}")
    
    if optional_missing:
        print(f"ℹ️  可选配置未设置（仅影响反向同步功能）: {', '.join(optional_missing)}")
    
    if not missing_configs and not placeholder_configs:
        print("✅ .env文件核心配置验证通过")
        if not optional_missing:
            print("✅ 可选配置也已完整，支持双向同步")
        else:
            print("ℹ️  当前仅支持单向同步（Notion → JIRA）")
        return True
    
    return False


def main():
    """主函数"""
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python init_config.py create   # 创建.env文件")
        print("  python init_config.py validate # 验证.env文件")
        return
    
    command = sys.argv[1]
    
    if command == 'create':
        create_env_file()
    elif command == 'validate':
        validate_env_file()
    else:
        print(f"未知命令: {command}")
        print("支持的命令: create, validate")


if __name__ == "__main__":
    main() 