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

    # 4. 使用 REST API 创建一个新的 Issue
    new_issue_summary = "REST API 测试 - 新建任务"
    new_issue_description = "这是一个通过 Python REST API 脚本自动创建的测试任务。\n用于验证 JIRA REST API 的创建功能。"
    created_issue_key = create_issue_rest_api(
        project_key=TEST_PROJECT_KEY,
        summary=new_issue_summary,
        description=new_issue_description,
        issue_type_name=TEST_ISSUE_TYPE_NAME
    )

    # 5. 读取刚创建的 Issue
    if created_issue_key:
        get_issue(created_issue_key)
        
        # 6. 使用 REST API 向刚创建的Issue添加评论
        add_comment_rest_api(
            issue_key=created_issue_key,
            comment_text="这是一条通过 REST API 添加的测试评论。用于验证评论功能。"
        )
        
        # 7. 使用 REST API 更新刚创建的Issue
        update_issue_rest_api(
            issue_key=created_issue_key,
            fields_to_update={
                "summary": f"{new_issue_summary} - 已通过REST API更新",
                "description": f"{new_issue_description}\n\n此描述已通过 REST API 更新。"
            }
        )
        
        # 8. 再次读取Issue以验证更新
        print("验证更新结果:")
        get_issue(created_issue_key)
        
    else:
        print("由于创建 Issue 失败，跳过后续的读取、更新和评论测试。\n")

    # 9. 读取一个已知的 Issue
    known_issue_key_default = f"{TEST_PROJECT_KEY}-1"
    user_input_known_issue = input(f"请输入一个您项目中已知的 Issue Key 进行读取测试 (例如 {known_issue_key_default}，直接回车使用此默认值): ").strip()
    known_issue_key_to_test = user_input_known_issue if user_input_known_issue else known_issue_key_default
    get_issue(known_issue_key_to_test)
    
    # 10. 使用 JQL 搜索 Issues
    jql_query_example = f"project = {TEST_PROJECT_KEY} AND issuetype = {TEST_ISSUE_TYPE_NAME} ORDER BY created DESC"
    search_issues(jql_query_example)

    print("--- JIRA REST API 测试完成 ---") 