#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notion2JIRA 字段映射分析器

此脚本用于分析 JIRA 项目的字段配置，生成详细的字段映射报告，
并更新相关文档。主要功能包括：

1. 获取 JIRA 项目的所有可用状态
2. 获取系统优先级信息
3. 获取项目可分配用户
4. 获取项目版本信息
5. 生成完整的字段映射表格
6. 更新 NOTION_WEBHOOK_SPEC.md 文档

使用方法:
    python field_mapping_analyzer.py

环境变量配置:
    JIRA_BASE_URL: JIRA 服务器地址
    JIRA_USER_EMAIL: JIRA 用户邮箱
    JIRA_USER_PASSWORD: JIRA 用户密码
    TEST_PROJECT_KEY: 测试项目Key
    TEST_ISSUE_TYPE_NAME: 测试Issue类型名称
"""

import requests
import json
import warnings
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import re

# 加载环境变量
load_dotenv()

# --- 配置区域 ---
JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "http://rdjira.tp-link.com")
USER_EMAIL = os.environ.get("JIRA_USER_EMAIL", "")
USER_PASSWORD = os.environ.get("JIRA_USER_PASSWORD", "")
VERIFY_SSL = os.environ.get("VERIFY_SSL", "False").lower() in ("true", "1", "yes")
TEST_PROJECT_KEY = os.environ.get("TEST_PROJECT_KEY", "SMBNET")
TEST_ISSUE_TYPE_NAME = os.environ.get("TEST_ISSUE_TYPE_NAME", "Story")

# 全局会话
session = requests.Session()

def setup_authentication():
    """设置 JIRA API 认证"""
    print(f"正在为用户 {USER_EMAIL} 设置 JIRA REST API 认证...")
    
    if not USER_PASSWORD or USER_PASSWORD == "YOUR_PASSWORD_HERE":
        print("错误：请在环境变量中设置 'JIRA_USER_PASSWORD' 为您的实际密码。")
        exit(1)
    
    global session
    session = requests.Session()
    session.auth = (USER_EMAIL, USER_PASSWORD)
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Notion2JIRA-Field-Mapper/1.0"
    })
    
    if not VERIFY_SSL:
        warnings.filterwarnings('ignore', message='Unverified HTTPS request')
        print("Warning: SSL certificate verification is disabled!")
    
    print("REST API 认证信息已设置。\n")

def test_connection():
    """测试 JIRA 连接"""
    print("--- 测试 JIRA 连接 ---")
    api_url = f"{JIRA_BASE_URL}/rest/api/2/myself"
    
    try:
        response = session.get(api_url, verify=VERIFY_SSL, timeout=30)
        response.raise_for_status()
        user_data = response.json()
        print(f"连接成功！当前用户: {user_data.get('displayName')} ({user_data.get('emailAddress')})")
        return True
    except Exception as e:
        print(f"连接失败: {e}")
        return False

def get_project_statuses(project_key):
    """获取项目的所有可用状态"""
    print(f"--- 获取项目 {project_key} 的状态信息 ---")
    api_url = f"{JIRA_BASE_URL}/rest/api/2/project/{project_key}/statuses"
    
    try:
        response = session.get(api_url, verify=VERIFY_SSL)
        response.raise_for_status()
        statuses_data = response.json()
        
        all_statuses = []
        print(f"项目状态信息:")
        
        for issue_type_statuses in statuses_data:
            issue_type_name = issue_type_statuses.get('name', 'Unknown')
            statuses = issue_type_statuses.get('statuses', [])
            
            print(f"  Issue类型: {issue_type_name}")
            for status in statuses:
                status_info = {
                    'id': status.get('id'),
                    'name': status.get('name'),
                    'description': status.get('description', ''),
                    'issue_type': issue_type_name
                }
                all_statuses.append(status_info)
                print(f"    - ID: {status.get('id')}, 名称: {status.get('name')}")
        
        print(f"获取到 {len(all_statuses)} 个状态。\n")
        return all_statuses
        
    except Exception as e:
        print(f"获取项目状态失败: {e}\n")
        return None

def get_priorities():
    """获取系统的所有优先级"""
    print("--- 获取系统优先级信息 ---")
    api_url = f"{JIRA_BASE_URL}/rest/api/2/priority"
    
    try:
        response = session.get(api_url, verify=VERIFY_SSL)
        response.raise_for_status()
        priorities_data = response.json()
        
        print(f"系统优先级信息:")
        priorities = []
        for priority in priorities_data:
            priority_info = {
                'id': priority.get('id'),
                'name': priority.get('name'),
                'description': priority.get('description', ''),
                'iconUrl': priority.get('iconUrl', '')
            }
            priorities.append(priority_info)
            print(f"  - ID: {priority.get('id')}, 名称: {priority.get('name')}")
        
        print(f"获取到 {len(priorities)} 个优先级。\n")
        return priorities
        
    except Exception as e:
        print(f"获取系统优先级失败: {e}\n")
        return None

def get_project_users(project_key):
    """获取项目的可分配用户"""
    print(f"--- 获取项目 {project_key} 的可分配用户 ---")
    api_url = f"{JIRA_BASE_URL}/rest/api/2/user/assignable/search"
    params = {
        "project": project_key,
        "maxResults": 100
    }
    
    try:
        response = session.get(api_url, params=params, verify=VERIFY_SSL)
        response.raise_for_status()
        users_data = response.json()
        
        print(f"项目可分配用户信息:")
        users = []
        for user in users_data:
            user_info = {
                'accountId': user.get('accountId'),
                'name': user.get('name'),
                'displayName': user.get('displayName'),
                'emailAddress': user.get('emailAddress'),
                'active': user.get('active', True)
            }
            users.append(user_info)
            print(f"  - 用户名: {user.get('name')}, 显示名: {user.get('displayName')}, 邮箱: {user.get('emailAddress')}")
        
        print(f"获取到 {len(users)} 个可分配用户。\n")
        return users
        
    except Exception as e:
        print(f"获取项目用户失败: {e}\n")
        return None

def get_project_versions(project_key):
    """获取项目的可用版本信息"""
    print(f"--- 获取项目 {project_key} 的版本信息 ---")
    api_url = f"{JIRA_BASE_URL}/rest/api/2/project/{project_key}/versions"
    
    try:
        response = session.get(api_url, verify=VERIFY_SSL)
        response.raise_for_status()
        versions_data = response.json()
        
        print(f"项目版本信息:")
        if not versions_data:
            print("  该项目没有配置版本")
            return []
            
        versions = []
        for version in versions_data:
            version_info = {
                'id': version.get('id'),
                'name': version.get('name'),
                'released': version.get('released', False),
                'description': version.get('description', '')
            }
            versions.append(version_info)
            print(f"  - ID: {version.get('id')}, 名称: {version.get('name')}, 已发布: {version.get('released', False)}")
        
        print(f"获取到 {len(versions)} 个版本。\n")
        return versions
        
    except Exception as e:
        print(f"获取项目版本失败: {e}\n")
        return []

def generate_field_mapping_report(project_key, issue_type_name="Story"):
    """生成完整的字段映射报告"""
    print("=== 生成 Notion2JIRA 字段映射报告 ===\n")
    
    # 获取各种字段信息
    statuses = get_project_statuses(project_key)
    priorities = get_priorities()
    users = get_project_users(project_key)
    versions = get_project_versions(project_key)
    
    # 定义Notion到JIRA的字段映射
    field_mapping = [
        {
            "字段": "需求名",
            "Notion字段名": "功能 Name",
            "Notion字段类型": "title",
            "字段详情": "示例：\"roaming等功能联动wifi navi\"",
            "JIRA字段名": "Summary",
            "字段详情_JIRA": "",
            "备注": ""
        },
        {
            "字段": "需求状态",
            "Notion字段名": "Status",
            "Notion字段类型": "status",
            "字段详情": "初始反馈 OR\n待评估 UR\n待输入 WI\n同步中 SYNC\n已输入 JIRA\nPRD Done\nUI Done\nUX Done\nDEVING\nDELAYED\n已发布 DONE\n重复 DUMP\n无效 INVALID\n暂不支持 PENDING\n无法支持 BAN",
            "JIRA字段名": "Status",
            "字段详情_JIRA": "",
            "备注": ""
        },
        {
            "字段": "优先级",
            "Notion字段名": "优先级 P",
            "Notion字段类型": "select",
            "字段详情": "高 High\n中 Medium\n低 Low\n无 None",
            "JIRA字段名": "Priority",
            "字段详情_JIRA": "",
            "备注": ""
        },
        {
            "字段": "需求说明",
            "Notion字段名": "功能说明 Desc",
            "Notion字段类型": "rich_text",
            "字段详情": "",
            "JIRA字段名": "Description",
            "字段详情_JIRA": "",
            "备注": ""
        },
        {
            "字段": "需求整理(AI)",
            "Notion字段名": "需求整理",
            "Notion字段类型": "rich_text",
            "字段详情": "markdown 格式的需求富文本",
            "JIRA字段名": "Description",
            "字段详情_JIRA": "",
            "备注": ""
        },
        {
            "字段": "url",
            "Notion字段名": "url",
            "Notion字段类型": "url",
            "字段详情": "",
            "JIRA字段名": "Description",
            "字段详情_JIRA": "Description 中会写入 需求说明 + 需求整理 + Notion对应需求链接",
            "备注": ""
        },
        {
            "字段": "创建者",
            "Notion字段名": "无",
            "Notion字段类型": "无",
            "字段详情": "",
            "JIRA字段名": "Reporter",
            "字段详情_JIRA": "",
            "备注": "无须配置，默认为脚本账号： lucien.chen@tp-link.com"
        },
        {
            "字段": "分配者",
            "Notion字段名": "需求录入",
            "Notion字段类型": "people",
            "字段详情": "email格式",
            "JIRA字段名": "Assignee",
            "字段详情_JIRA": "写入对应 email",
            "备注": ""
        },
        {
            "字段": "实现版本",
            "Notion字段名": "关联项目",
            "Notion字段类型": "relation",
            "字段详情": "",
            "JIRA字段名": "fixVersions",
            "字段详情_JIRA": "",
            "备注": ""
        },
        {
            "字段": "关联链接",
            "Notion字段名": "JIRA Card",
            "Notion字段类型": "url",
            "字段详情": "",
            "JIRA字段名": "无",
            "字段详情_JIRA": "",
            "备注": "写入JIRA 后需要回写 Notion 的字段，内容为 JIRA Card 链接"
        }
    ]
    
    # 更新字段详情
    if statuses:
        status_names = [status['name'] for status in statuses if status['issue_type'] == issue_type_name]
        if status_names:
            for mapping in field_mapping:
                if mapping["JIRA字段名"] == "Status":
                    mapping["字段详情_JIRA"] = "\n".join(status_names)
    
    if priorities:
        priority_names = [priority['name'] for priority in priorities]
        for mapping in field_mapping:
            if mapping["JIRA字段名"] == "Priority":
                mapping["字段详情_JIRA"] = "\n".join(priority_names)
    
    if users:
        user_emails = [user['emailAddress'] for user in users if user['emailAddress']]
        for mapping in field_mapping:
            if mapping["JIRA字段名"] == "Assignee":
                mapping["字段详情_JIRA"] = f"可分配用户邮箱列表（共{len(user_emails)}个）:\n" + "\n".join(user_emails[:10])
                if len(user_emails) > 10:
                    mapping["字段详情_JIRA"] += f"\n... 还有 {len(user_emails) - 10} 个用户"
    
    if versions:
        version_names = [version['name'] for version in versions]
        for mapping in field_mapping:
            if mapping["JIRA字段名"] == "fixVersions":
                mapping["字段详情_JIRA"] = "\n".join(version_names) if version_names else "无可用版本"
    
    # 生成报告
    print("字段映射表格:")
    print("=" * 120)
    
    # 打印表格头
    print(f"{'字段':<12} {'Notion字段名':<15} {'Notion字段类型':<15} {'JIRA字段名':<12} {'备注':<30}")
    print("-" * 120)
    
    # 打印每一行
    for mapping in field_mapping:
        print(f"{mapping['字段']:<12} {mapping['Notion字段名']:<15} {mapping['Notion字段类型']:<15} {mapping['JIRA字段名']:<12} {mapping['备注']:<30}")
    
    print("=" * 120)
    print()
    
    # 详细信息
    print("详细字段信息:")
    print("=" * 80)
    
    for mapping in field_mapping:
        print(f"\n字段: {mapping['字段']}")
        print(f"  Notion字段名: {mapping['Notion字段名']}")
        print(f"  Notion字段类型: {mapping['Notion字段类型']}")
        if mapping['字段详情']:
            print(f"  Notion字段详情: {mapping['字段详情']}")
        print(f"  JIRA字段名: {mapping['JIRA字段名']}")
        if mapping['字段详情_JIRA']:
            print(f"  JIRA字段详情: {mapping['字段详情_JIRA']}")
        if mapping['备注']:
            print(f"  备注: {mapping['备注']}")
    
    # 保存到文件
    try:
        # 创建DataFrame
        df = pd.DataFrame(field_mapping)
        
        # 保存为CSV
        csv_filename = f"notion2jira_field_mapping_{project_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"\n字段映射表格已保存到: {csv_filename}")
        
        # 保存为Excel
        excel_filename = f"notion2jira_field_mapping_{project_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(excel_filename, index=False, engine='openpyxl')
        print(f"字段映射表格已保存到: {excel_filename}")
        
    except ImportError:
        print("\n注意: 需要安装 pandas 和 openpyxl 来保存Excel文件")
        print("运行: pip install pandas openpyxl")
    except Exception as e:
        print(f"\n保存文件时出错: {e}")
    
    return field_mapping

def update_notion_webhook_spec(field_mapping):
    """更新 NOTION_WEBHOOK_SPEC.md 文档中的字段映射表格"""
    print("--- 更新 NOTION_WEBHOOK_SPEC.md 文档 ---")
    
    try:
        # 读取现有文档
        with open('NOTION_WEBHOOK_SPEC.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 生成新的映射表格
        new_table = "## 完整字段映射表\n\n"
        new_table += "| Notion 字段名 | 字段类型 | 解析后的值 | JIRA 映射字段 | 说明 |\n"
        new_table += "|---------------|----------|------------|---------------|------|\n"
        
        for mapping in field_mapping:
            notion_field = mapping['Notion字段名']
            notion_type = mapping['Notion字段类型']
            example_value = mapping['字段详情'].split('\n')[0] if mapping['字段详情'] else ""
            jira_field = mapping['JIRA字段名']
            note = mapping['备注'] or mapping['字段详情_JIRA'].split('\n')[0] if mapping['字段详情_JIRA'] else ""
            
            new_table += f"| `{notion_field}` | {notion_type} | \"{example_value}\" | {jira_field} | {note} |\n"
        
        # 查找并替换现有的映射表格
        pattern = r'## 完整字段映射表.*?(?=\n## |\n# |\Z)'
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, new_table.rstrip(), content, flags=re.DOTALL)
        else:
            # 如果没找到，添加到文档末尾
            content += "\n\n" + new_table
        
        # 写回文件
        with open('NOTION_WEBHOOK_SPEC.md', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("NOTION_WEBHOOK_SPEC.md 文档已更新")
        
    except FileNotFoundError:
        print("未找到 NOTION_WEBHOOK_SPEC.md 文件")
    except Exception as e:
        print(f"更新文档时出错: {e}")

def main():
    """主函数"""
    print("Notion2JIRA 字段映射分析器")
    print("=" * 50)
    print(f"项目: {TEST_PROJECT_KEY}")
    print(f"Issue类型: {TEST_ISSUE_TYPE_NAME}")
    print(f"JIRA服务器: {JIRA_BASE_URL}")
    print("=" * 50)
    print()
    
    # 1. 设置认证
    setup_authentication()
    
    # 2. 测试连接
    if not test_connection():
        print("无法连接到 JIRA，请检查配置。")
        return
    
    # 3. 生成字段映射报告
    field_mapping = generate_field_mapping_report(TEST_PROJECT_KEY, TEST_ISSUE_TYPE_NAME)
    
    # 4. 更新文档
    if field_mapping:
        update_notion_webhook_spec(field_mapping)
        print("\n=== 字段映射分析完成 ===")
        print("报告已生成并保存到文件。")
        print("NOTION_WEBHOOK_SPEC.md 文档已更新。")
    else:
        print("字段映射分析失败。")

if __name__ == "__main__":
    main() 