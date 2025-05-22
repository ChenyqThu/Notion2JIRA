import requests
import warnings
import json

# 忽略HTTPS警告
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# JIRA服务器URL
JIRA_BASE_URL = "http://rdjira.tp-link.com"
USER_EMAIL = "lucien.chen@tp-link.com"
USER_PASSWORD = "~!@#CyQ1611"

# 配置项目和Issue类型
PROJECT_KEY = "SMBNET"  # 修改为正确的项目键
ISSUE_TYPE_NAME = "Story" # 对应ID: 10001 (根据您的api.md)

# 创建Session并配置
session = requests.Session()
session.auth = (USER_EMAIL, USER_PASSWORD)
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "X-Requested-With": "XMLHttpRequest"
})

# 步骤1: 获取表单令牌和XSRF令牌
print("获取必要的令牌...")
try:
    # 先获取Dashboard页面以获取必要的Cookie
    dashboard_url = f"{JIRA_BASE_URL}/secure/Dashboard.jspa"
    dashboard_response = session.get(dashboard_url)
    dashboard_response.raise_for_status()
    
    # 从Cookie中提取XSRF令牌
    xsrf_token = None
    for cookie in session.cookies:
        if cookie.name == 'atlassian.xsrf.token':
            xsrf_token = cookie.value
            print(f"已获取XSRF令牌: {xsrf_token[:10]}...")
            break
    
    if not xsrf_token:
        print("错误: 无法获取XSRF令牌，无法创建Issue")
        exit(1)
    
    # 获取项目页面以获取更多必要的表单值
    # 使用正确的项目URL
    project_url = f"{JIRA_BASE_URL}/browse/{PROJECT_KEY}"
    print(f"访问项目页面: {project_url}")
    project_response = session.get(project_url)
    project_response.raise_for_status()
    
    # 获取可用的解决版本
    print("获取可用的解决版本...")
    versions_url = f"{JIRA_BASE_URL}/rest/api/2/project/{PROJECT_KEY}/versions"
    versions_response = session.get(versions_url)
    versions_response.raise_for_status()
    
    versions = versions_response.json()
    print(f"找到 {len(versions)} 个版本:")
    for i, version in enumerate(versions[:5]):  # 只显示前5个版本
        print(f"  {i+1}. ID: {version.get('id')}, 名称: {version.get('name')}")
    
    # 使用api.md中提供的版本ID
    fix_version_id = "14613"  # 从您提供的API数据中获取
    print(f"将使用版本ID: {fix_version_id}")
    
    # 尝试创建Issue
    issue_summary = "API表单测试 - 新建任务 (模拟表单)"
    issue_description = "这是一个通过Python脚本模拟表单提交自动创建的测试任务。\n用于验证JIRA表单提交API。"
    
    # 步骤2: 准备表单数据
    form_data = {
        "pid": "13904",  # 从您的api.md中获取的项目ID
        "issuetype": "10001",  # 从您的api.md中获取的Issue类型ID (Story)
        "atl_token": xsrf_token,
        "summary": issue_summary,
        "description": issue_description,
        "fixVersions": fix_version_id,  # 必填项
        "isCreateIssue": "true",
        "isEditIssue": "false",
        "priority": "3",
    }
    
    # 从api.md添加额外的表单字段，以确保成功
    additional_fields = {
        "formToken": "",  # 可能需要从页面中提取
        "assignee": "-1",
        "customfield_11302": "",
        "customfield_10006": "",
        "timetracking_originalestimate": "",
        "hasWorkStarted": "",
        "timetracking_remainingestimate": "",
        "worklog_timeLogged": "",
        "worklog_adjustEstimate": "auto",
        "comment": ""
    }
    
    form_data.update(additional_fields)
    
    # 添加fieldsToRetain字段列表
    fields_to_retain = [
        "project", "issuetype", "versions", "fixVersions", "components", 
        "assignee", "customfield_10005", "customfield_11302", "customfield_10006", 
        "labels", "priority", "customfield_10001", "customfield_10700", 
        "customfield_10704", "customfield_10203", "customfield_10701", "customfield_10717"
    ]
    
    # 为每个字段添加一个表单条目
    form_data_with_fields = {}
    for key, value in form_data.items():
        form_data_with_fields[key] = value
    
    for field in fields_to_retain:
        form_data_with_fields[f"fieldsToRetain"] = field
    
    # 步骤3: 提交创建Issue的请求
    print(f"尝试创建Issue: {issue_summary}")
    create_url = f"{JIRA_BASE_URL}/secure/QuickCreateIssue.jspa?decorator=none"
    
    # 配置特定的请求头
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": project_url,
        "Origin": JIRA_BASE_URL,
        "DNT": "1",
    }
    
    create_response = session.post(
        create_url,
        data=form_data_with_fields,
        headers=headers
    )
    
    # 检查响应
    if create_response.status_code == 200:
        print("Issue创建成功！")
        print(f"响应内容: {create_response.text[:200]}...")  # 截取前200字符显示
        
        # 尝试从响应中提取Issue Key
        try:
            if "issueKey" in create_response.text:
                import re
                issue_key_match = re.search(r'"issueKey":"([^"]+)"', create_response.text)
                if issue_key_match:
                    issue_key = issue_key_match.group(1)
                    print(f"创建的Issue Key: {issue_key}")
                    print(f"Issue链接: {JIRA_BASE_URL}/browse/{issue_key}")
        except:
            pass
    else:
        print(f"创建失败。状态码: {create_response.status_code}")
        print(f"响应内容: {create_response.text}")
    
except requests.exceptions.RequestException as e:
    print(f"请求异常: {e}")
except Exception as e:
    print(f"发生错误: {e}") 