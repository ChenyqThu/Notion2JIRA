import requests
import json
import warnings
import ssl
import os
from requests.adapters import HTTPAdapter
try:
    from urllib3.poolmanager import PoolManager
except ImportError:
    from requests.packages.urllib3.poolmanager import PoolManager
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime

# 加载环境变量
load_dotenv()

# --- 配置区域 ---
# 从环境变量获取配置
JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "http://rdjira.tp-link.com")
USER_EMAIL = os.environ.get("JIRA_USER_EMAIL", "")
USER_PASSWORD = os.environ.get("JIRA_USER_PASSWORD", "")

# SSL 验证配置
VERIFY_SSL = os.environ.get("VERIFY_SSL", "False").lower() in ("true", "1", "yes")

# 测试项目配置
TEST_PROJECT_KEY = os.environ.get("TEST_PROJECT_KEY", "SMBNET")
TEST_ISSUE_TYPE_NAME = os.environ.get("TEST_ISSUE_TYPE_NAME", "Story")

# --- 全局会话 ---
session = requests.Session()

def setup_authentication():
    """
    设置 JIRA API 的 Basic Authentication
    """
    print(f"正在为用户 {USER_EMAIL} 设置 JIRA REST API 认证...")
    if USER_PASSWORD == "YOUR_PASSWORD_HERE" or not USER_PASSWORD:
        print("错误：请在环境变量中设置 'JIRA_USER_PASSWORD' 为您的实际密码。")
        print("出于安全考虑，脚本将退出。")
        exit()
    
    # 重置session
    global session
    session = requests.Session()
    
    # 设置基本认证
    session.auth = (USER_EMAIL, USER_PASSWORD)
    
    # 设置请求头
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Python-JIRA-REST-Client/1.0"
    })
    
    # 忽略SSL警告
    if not VERIFY_SSL:
        warnings.filterwarnings('ignore', message='Unverified HTTPS request')
        print("Warning: SSL certificate verification is disabled!")
        
    print("REST API 认证信息已设置。")
    print("")

def test_connection():
    """
    测试与 JIRA REST API 的基本连接和认证
    """
    print("--- 测试 REST API 连接与认证 ---")
    api_url = f"{JIRA_BASE_URL}/rest/api/2/myself"
    
    try:
        print(f"尝试连接: {api_url}")
        response = session.get(api_url, verify=VERIFY_SSL, timeout=30)
        response.raise_for_status()
        user_data = response.json()
        print(f"连接成功！获取到用户信息：")
        print(f"  用户名: {user_data.get('name')}")
        print(f"  显示名称: {user_data.get('displayName')}")
        print(f"  邮箱: {user_data.get('emailAddress')}")
        print("REST API 连接与认证测试通过。\n")
        return True
    except requests.exceptions.Timeout:
        print(f"连接超时。请检查网络连接或服务器状态。")
    except requests.exceptions.SSLError as ssl_err:
        print(f"SSL 错误: {ssl_err}")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err}")
        if hasattr(http_err, 'response') and http_err.response is not None:
            print(f"响应内容: {http_err.response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    except json.JSONDecodeError:
        print("错误：无法解析响应为 JSON。可能是认证失败或 URL 不正确。")
        if 'response' in locals():
            print(f"响应内容: {response.text}")
    
    print("REST API 连接与认证测试失败。\n")
    return False

def get_project_info(project_key):
    """
    获取项目信息，包括项目ID和可用的issue类型
    """
    print(f"--- 获取项目 {project_key} 信息 ---")
    api_url = f"{JIRA_BASE_URL}/rest/api/2/project/{project_key}"
    
    try:
        response = session.get(api_url, verify=VERIFY_SSL)
        response.raise_for_status()
        project_data = response.json()
        
        print(f"项目信息:")
        print(f"  项目ID: {project_data.get('id')}")
        print(f"  项目名称: {project_data.get('name')}")
        print(f"  项目Key: {project_data.get('key')}")
        
        # 获取可用的issue类型
        issue_types = project_data.get('issueTypes', [])
        print(f"  可用Issue类型:")
        for issue_type in issue_types:
            print(f"    - ID: {issue_type.get('id')}, 名称: {issue_type.get('name')}")
        
        print("获取项目信息成功。\n")
        return project_data
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err}")
        if hasattr(http_err, 'response') and http_err.response is not None:
            print(f"响应内容: {http_err.response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    
    print("获取项目信息失败。\n")
    return None

def get_create_meta(project_key):
    """
    获取创建issue的元数据信息
    """
    print(f"--- 获取项目 {project_key} 的创建元数据 ---")
    api_url = f"{JIRA_BASE_URL}/rest/api/2/issue/createmeta"
    params = {
        "projectKeys": project_key,
        "expand": "projects.issuetypes.fields"
    }
    
    try:
        response = session.get(api_url, params=params, verify=VERIFY_SSL)
        response.raise_for_status()
        meta_data = response.json()
        
        projects = meta_data.get('projects', [])
        if projects:
            project = projects[0]
            print(f"项目: {project.get('name')} (ID: {project.get('id')})")
            
            issue_types = project.get('issuetypes', [])
            print(f"可创建的Issue类型:")
            for issue_type in issue_types:
                print(f"  - {issue_type.get('name')} (ID: {issue_type.get('id')})")
                
                # 显示必填字段
                fields = issue_type.get('fields', {})
                required_fields = [field_key for field_key, field_info in fields.items() 
                                 if field_info.get('required', False)]
                if required_fields:
                    print(f"    必填字段: {', '.join(required_fields)}")
        
        print("获取创建元数据成功。\n")
        return meta_data
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err}")
        if hasattr(http_err, 'response') and http_err.response is not None:
            print(f"响应内容: {http_err.response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    
    print("获取创建元数据失败。\n")
    return None

def get_project_versions(project_key):
    """
    获取项目的可用版本信息
    """
    print(f"--- 获取项目 {project_key} 的版本信息 ---")
    api_url = f"{JIRA_BASE_URL}/rest/api/2/project/{project_key}/versions"
    
    try:
        response = session.get(api_url, verify=VERIFY_SSL)
        response.raise_for_status()
        versions_data = response.json()
        
        print(f"项目版本信息:")
        if not versions_data:
            print("  该项目没有配置版本")
            return None
            
        for version in versions_data:
            print(f"  - ID: {version.get('id')}, 名称: {version.get('name')}, 已发布: {version.get('released', False)}")
        
        # 返回第一个未发布的版本，如果没有则返回第一个版本
        unreleased_versions = [v for v in versions_data if not v.get('released', False)]
        if unreleased_versions:
            selected_version = unreleased_versions[0]
            print(f"  选择未发布版本: {selected_version.get('name')} (ID: {selected_version.get('id')})")
        else:
            selected_version = versions_data[0]
            print(f"  选择第一个版本: {selected_version.get('name')} (ID: {selected_version.get('id')})")
        
        print("获取项目版本信息成功。\n")
        return selected_version
        
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err}")
        if hasattr(http_err, 'response') and http_err.response is not None:
            print(f"响应内容: {http_err.response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    
    print("获取项目版本信息失败。\n")
    return None

def create_issue_rest_api(project_key, summary, description, issue_type_name="Story"):
    """
    使用 REST API 创建 JIRA Issue
    """
    print(f"--- 使用 REST API 创建新 Issue ---")
    
    # 首先获取项目信息以找到正确的项目ID和issue类型ID
    project_info = get_project_info(project_key)
    if not project_info:
        print("无法获取项目信息，创建失败。")
        return None
    
    project_id = project_info.get('id')
    issue_types = project_info.get('issueTypes', [])
    
    # 查找指定的issue类型ID
    issue_type_id = None
    for issue_type in issue_types:
        if issue_type.get('name') == issue_type_name:
            issue_type_id = issue_type.get('id')
            break
    
    if not issue_type_id:
        print(f"未找到issue类型 '{issue_type_name}'")
        print(f"可用的issue类型: {[it.get('name') for it in issue_types]}")
        return None
    
    # 获取项目版本信息
    version_info = get_project_versions(project_key)
    if not version_info:
        print("无法获取项目版本信息，尝试使用硬编码版本ID...")
        # 使用原来test.py中的硬编码版本ID作为备选
        version_id = "14613"
        print(f"使用硬编码版本ID: {version_id}")
    else:
        version_id = version_info.get('id')
        print(f"使用获取到的版本ID: {version_id}")
    
    # 构建创建issue的payload，包含必填的fixVersions字段
    payload = {
        "fields": {
            "project": {
                "id": project_id
            },
            "summary": summary,
            "description": description,
            "issuetype": {
                "id": issue_type_id
            },
            "fixVersions": [
                {
                    "id": version_id
                }
            ]
        }
    }
    
    api_url = f"{JIRA_BASE_URL}/rest/api/2/issue"
    
    try:
        print(f"尝试在项目 '{project_key}' 中创建类型为 '{issue_type_name}' 的 Issue")
        print(f"标题: '{summary}'")
        print(f"使用版本ID: {version_id}")
        
        response = session.post(api_url, json=payload, verify=VERIFY_SSL)
        response.raise_for_status()
        
        issue_data = response.json()
        issue_key = issue_data.get('key')
        issue_id = issue_data.get('id')
        
        print(f"Issue创建成功！")
        print(f"  Issue Key: {issue_key}")
        print(f"  Issue ID: {issue_id}")
        print(f"  Issue链接: {JIRA_BASE_URL}/browse/{issue_key}")
        print("使用 REST API 创建 Issue 成功。\n")
        
        return issue_key
        
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err}")
        if hasattr(http_err, 'response') and http_err.response is not None:
            try:
                error_json = http_err.response.json()
                print("错误详情:")
                if "errorMessages" in error_json:
                    print(f"  Messages: {error_json['errorMessages']}")
                if "errors" in error_json:
                    print(f"  Errors: {error_json['errors']}")
            except json.JSONDecodeError:
                print(f"  响应内容: {http_err.response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    except Exception as e:
        print(f"发生未预期错误: {e}")
    
    print("使用 REST API 创建 Issue 失败。\n")
    return None

def add_comment_rest_api(issue_key, comment_text):
    """
    使用 REST API 向 JIRA Issue 添加评论
    """
    print(f"--- 使用 REST API 向 Issue: {issue_key} 添加评论 ---")
    
    payload = {
        "body": comment_text
    }
    
    api_url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_key}/comment"
    
    try:
        print(f"尝试向 Issue '{issue_key}' 添加评论")
        
        response = session.post(api_url, json=payload, verify=VERIFY_SSL)
        response.raise_for_status()
        
        comment_data = response.json()
        comment_id = comment_data.get('id')
        
        print(f"评论添加成功！")
        print(f"  评论ID: {comment_id}")
        print(f"  评论内容: {comment_text}")
        print("使用 REST API 添加评论成功。\n")
        
        return comment_data
        
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err}")
        if hasattr(http_err, 'response') and http_err.response is not None:
            try:
                error_json = http_err.response.json()
                print("错误详情:")
                if "errorMessages" in error_json:
                    print(f"  Messages: {error_json['errorMessages']}")
                if "errors" in error_json:
                    print(f"  Errors: {error_json['errors']}")
            except json.JSONDecodeError:
                print(f"  响应内容: {http_err.response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    except Exception as e:
        print(f"发生未预期错误: {e}")
    
    print("使用 REST API 添加评论失败。\n")
    return None

def get_issue(issue_key):
    """
    读取（获取）指定 JIRA Issue 的信息
    """
    print(f"--- 读取 Issue: {issue_key} ---")
    api_url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_key}"
    
    try:
        response = session.get(api_url, verify=VERIFY_SSL)
        response.raise_for_status()
        issue_data = response.json()
        
        fields = issue_data.get('fields', {})
        print(f"成功获取 Issue '{issue_key}' 的信息:")
        print(f"  标题 (Summary): {fields.get('summary')}")
        print(f"  描述 (Description): {fields.get('description', '')[:100]}...")
        print(f"  状态 (Status): {fields.get('status', {}).get('name')}")
        print(f"  创建者 (Reporter): {fields.get('reporter', {}).get('displayName')}")
        print(f"  分配给 (Assignee): {fields.get('assignee', {}).get('displayName') if fields.get('assignee') else '未分配'}")
        print(f"  优先级 (Priority): {fields.get('priority', {}).get('name')}")
        print(f"读取 Issue '{issue_key}' 成功。\n")
        return issue_data
        
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err}")
        if hasattr(http_err, 'response') and http_err.response is not None:
            print(f"响应内容: {http_err.response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    
    print(f"读取 Issue '{issue_key}' 失败。\n")
    return None

def update_issue_rest_api(issue_key, fields_to_update):
    """
    使用 REST API 更新 JIRA Issue 的字段
    """
    print(f"--- 使用 REST API 更新 Issue: {issue_key} ---")
    
    payload = {
        "fields": fields_to_update
    }
    
    api_url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_key}"
    
    try:
        print(f"尝试更新 Issue '{issue_key}' 的字段")
        
        response = session.put(api_url, json=payload, verify=VERIFY_SSL)
        response.raise_for_status()
        
        print(f"成功更新 Issue '{issue_key}' 的字段")
        print("使用 REST API 更新 Issue 成功。\n")
        return True
        
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err}")
        if hasattr(http_err, 'response') and http_err.response is not None:
            try:
                error_json = http_err.response.json()
                print("错误详情:")
                if "errorMessages" in error_json:
                    print(f"  Messages: {error_json['errorMessages']}")
                if "errors" in error_json:
                    print(f"  Errors: {error_json['errors']}")
            except json.JSONDecodeError:
                print(f"  响应内容: {http_err.response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    
    print(f"使用 REST API 更新 Issue '{issue_key}' 失败。\n")
    return False

def search_issues(jql_query):
    """
    使用 JQL 搜索 JIRA Issues
    """
    print(f"--- 搜索 Issues (JQL: {jql_query}) ---")
    api_url = f"{JIRA_BASE_URL}/rest/api/2/search"
    params = {"jql": jql_query, "maxResults": 5}
    
    try:
        response = session.get(api_url, params=params, verify=VERIFY_SSL)
        response.raise_for_status()
        search_results = response.json()
        
        total_issues = search_results.get('total', 0)
        issues_found = search_results.get('issues', [])
        
        print(f"搜索完成。总共找到 {total_issues} 个匹配的 Issue (显示前 {len(issues_found)} 个):")
        if not issues_found:
            print("  未找到匹配的 Issue。")
        for issue in issues_found:
            print(f"  - Key: {issue.get('key')}, 标题: {issue.get('fields', {}).get('summary')}")
        
        print("搜索 Issues 成功。\n")
        return search_results
        
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err}")
        if hasattr(http_err, 'response') and http_err.response is not None:
            print(f"响应内容: {http_err.response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    
    print("搜索 Issues 失败。\n")
    return None

def get_project_statuses(project_key):
    """
    获取项目的所有可用状态
    """
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
        
        print("获取项目状态信息成功。\n")
        return all_statuses
        
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err}")
        if hasattr(http_err, 'response') and http_err.response is not None:
            print(f"响应内容: {http_err.response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    
    print("获取项目状态信息失败。\n")
    return None

def get_priorities():
    """
    获取系统的所有优先级
    """
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
        
        print("获取系统优先级信息成功。\n")
        return priorities
        
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err}")
        if hasattr(http_err, 'response') and http_err.response is not None:
            print(f"响应内容: {http_err.response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    
    print("获取系统优先级信息失败。\n")
    return None

def get_project_users(project_key):
    """
    获取项目的可分配用户
    """
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
        
        print(f"获取项目可分配用户信息成功，共 {len(users)} 个用户。\n")
        return users
        
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err}")
        if hasattr(http_err, 'response') and http_err.response is not None:
            print(f"响应内容: {http_err.response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    
    print("获取项目可分配用户信息失败。\n")
    return None

def get_field_options(project_key, issue_type_name="Story"):
    """
    获取指定项目和Issue类型的所有字段选项
    """
    print(f"--- 获取项目 {project_key} Issue类型 {issue_type_name} 的字段选项 ---")
    
    # 首先获取创建元数据
    meta_data = get_create_meta(project_key)
    if not meta_data:
        return None
    
    projects = meta_data.get('projects', [])
    if not projects:
        print("未找到项目信息")
        return None
    
    project = projects[0]
    issue_types = project.get('issuetypes', [])
    
    # 找到指定的Issue类型
    target_issue_type = None
    for issue_type in issue_types:
        if issue_type.get('name') == issue_type_name:
            target_issue_type = issue_type
            break
    
    if not target_issue_type:
        print(f"未找到Issue类型: {issue_type_name}")
        return None
    
    fields = target_issue_type.get('fields', {})
    field_options = {}
    
    print(f"字段选项信息:")
    for field_key, field_info in fields.items():
        field_name = field_info.get('name', field_key)
        field_type = field_info.get('schema', {}).get('type', 'unknown')
        
        print(f"  字段: {field_name} ({field_key}) - 类型: {field_type}")
        
        # 获取选项值
        allowed_values = field_info.get('allowedValues', [])
        if allowed_values:
            options = []
            for value in allowed_values:
                if isinstance(value, dict):
                    option_info = {
                        'id': value.get('id'),
                        'name': value.get('name'),
                        'value': value.get('value', value.get('name'))
                    }
                    options.append(option_info)
                    print(f"    - ID: {value.get('id')}, 名称: {value.get('name')}")
                else:
                    options.append({'value': str(value)})
                    print(f"    - 值: {value}")
            
            field_options[field_key] = {
                'name': field_name,
                'type': field_type,
                'required': field_info.get('required', False),
                'options': options
            }
    
    print("获取字段选项信息成功。\n")
    return field_options

def generate_field_mapping_report(project_key, issue_type_name="Story"):
    """
    生成完整的字段映射报告
    """
    print("=== 生成 Notion2JIRA 字段映射报告 ===\n")
    
    # 获取各种字段信息
    statuses = get_project_statuses(project_key)
    priorities = get_priorities()
    users = get_project_users(project_key)
    versions = get_project_versions(project_key)
    field_options = get_field_options(project_key, issue_type_name)
    
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
        version_names = [version['name'] for version in versions if isinstance(versions, list)]
        if not version_names and isinstance(versions, dict):
            version_names = [versions['name']]
        for mapping in field_mapping:
            if mapping["JIRA字段名"] == "fixVersions":
                mapping["字段详情_JIRA"] = "\n".join(version_names) if version_names else "无可用版本"
    
    # 生成报告
    print("字段映射表格:")
    print("=" * 120)
    
    # 打印表格头
    headers = ["字段", "Notion字段名", "Notion字段类型", "字段详情", "JIRA字段名", "字段详情_JIRA", "备注"]
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
    """
    更新 NOTION_WEBHOOK_SPEC.md 文档中的字段映射表格
    """
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
        import re
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

if __name__ == "__main__":
    print("JIRA REST API 测试脚本")
    print("======================\n")

    # 1. 设置认证
    setup_authentication()

    # 2. 测试连接和认证
    if not test_connection():
        print("无法连接到 JIRA 或认证失败。请检查 JIRA URL、邮箱、密码以及网络连接。")
        exit()

    # 3. 获取项目信息和创建元数据
    print("获取项目信息和创建元数据...")
    get_project_info(TEST_PROJECT_KEY)
    get_create_meta(TEST_PROJECT_KEY)
    get_project_versions(TEST_PROJECT_KEY)

    # 4. 生成 Notion2JIRA 字段映射报告
    print("生成 Notion2JIRA 字段映射报告...")
    field_mapping = generate_field_mapping_report(TEST_PROJECT_KEY, TEST_ISSUE_TYPE_NAME)
    
    # 5. 更新文档
    if field_mapping:
        update_notion_webhook_spec(field_mapping)

    # 6. 使用 REST API 创建一个新的 Issue
    new_issue_summary = "REST API 测试 - 新建任务"
    new_issue_description = "这是一个通过 Python REST API 脚本自动创建的测试任务。\n用于验证 JIRA REST API 的创建功能。"
    created_issue_key = create_issue_rest_api(
        project_key=TEST_PROJECT_KEY,
        summary=new_issue_summary,
        description=new_issue_description,
        issue_type_name=TEST_ISSUE_TYPE_NAME
    )

    # 7. 读取刚创建的 Issue
    if created_issue_key:
        get_issue(created_issue_key)
        
        # 8. 使用 REST API 向刚创建的Issue添加评论
        add_comment_rest_api(
            issue_key=created_issue_key,
            comment_text="这是一条通过 REST API 添加的测试评论。用于验证评论功能。"
        )
        
        # 9. 使用 REST API 更新刚创建的Issue
        update_issue_rest_api(
            issue_key=created_issue_key,
            fields_to_update={
                "summary": f"{new_issue_summary} - 已通过REST API更新",
                "description": f"{new_issue_description}\n\n此描述已通过 REST API 更新。"
            }
        )
        
        # 10. 再次读取Issue以验证更新
        print("验证更新结果:")
        get_issue(created_issue_key)
        
    else:
        print("由于创建 Issue 失败，跳过后续的读取、更新和评论测试。\n")

    # 11. 读取一个已知的 Issue
    known_issue_key_default = f"{TEST_PROJECT_KEY}-1"
    user_input_known_issue = input(f"请输入一个您项目中已知的 Issue Key 进行读取测试 (例如 {known_issue_key_default}，直接回车使用此默认值): ").strip()
    known_issue_key_to_test = user_input_known_issue if user_input_known_issue else known_issue_key_default
    get_issue(known_issue_key_to_test)
    
    # 12. 使用 JQL 搜索 Issues
    jql_query_example = f"project = {TEST_PROJECT_KEY} AND issuetype = {TEST_ISSUE_TYPE_NAME} ORDER BY created DESC"
    search_issues(jql_query_example)

    print("--- JIRA REST API 测试完成 ---") 