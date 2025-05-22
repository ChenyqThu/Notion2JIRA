import requests
import json
import warnings # 用于处理 SSL 警告
import ssl
import os
from requests.adapters import HTTPAdapter
# urllib3.poolmanager might be under requests.packages.urllib3 for older requests versions
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
# !!! VERIFY_SSL = False 禁用 SSL 证书验证，会带来安全风险 (中间人攻击)。!!!
# !!! 仅在受信任的内部网络测试时使用。生产环境应始终为 True。!!!
VERIFY_SSL = os.environ.get("VERIFY_SSL", "False").lower() in ("true", "1", "yes") # 从环境变量读取

# 旧版 TLS 适配器配置
# !!! TRY_LEGACY_TLS_ADAPTER = True 会尝试使用可能较不安全的 TLS 配置以兼容旧服务器。!!!
# !!! 这可能解决 SSLEOFError 等握手问题，但会降低安全性。请谨慎使用。!!!
TRY_LEGACY_TLS_ADAPTER = os.environ.get("TRY_LEGACY_TLS_ADAPTER", "False").lower() in ("true", "1", "yes")

# HTTP 协议版本配置
# 某些服务器可能不支持默认的 HTTP/2，需要回退到 HTTP/1.1
USE_HTTP_1 = os.environ.get("USE_HTTP_1", "True").lower() in ("true", "1", "yes")

# 进行写测试时需要指定的项目 Key 和问题类型
TEST_PROJECT_KEY = os.environ.get("TEST_PROJECT_KEY", "SMBNET")
TEST_ISSUE_TYPE_NAME = os.environ.get("TEST_ISSUE_TYPE_NAME", "Story")

# --- 旧版 TLS 适配器定义 ---
# 创建一个自定义 SSL context，尝试兼容旧服务器
custom_ssl_context = ssl.create_default_context()
try:
    # 尝试禁用 TLS 1.3 (某些旧服务器可能无法正确处理 TLS 1.3 协商)
    # getattr is used for compatibility with older ssl modules that might not have OP_NO_TLSv1_3
    custom_ssl_context.options |= getattr(ssl, "OP_NO_TLSv1_3", 0) 
except AttributeError:
    print("Warning: Your Python's SSL module does not support OP_NO_TLSv1_3. Skipping this option.")

try:
    # 尝试设置更宽松的密码套件安全级别。
    # SECLEVEL=1 通常用于与旧系统兼容。SECLEVEL=0 更宽松但非常不安全。
    # 现代系统默认为 SECLEVEL=2。对于 JIRA 7.3.0，可能需要 SECLEVEL=1。
    custom_ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')
    print("Info: Legacy TLS Adapter will attempt to use ciphers 'DEFAULT@SECLEVEL=1'.")
except ssl.SSLError as e:
    print(f"Warning: Could not set ciphers to 'DEFAULT@SECLEVEL=1': {e}. Legacy TLS Adapter will use system default ciphers.")
except Exception as e:
    print(f"Warning: An unexpected error occurred while setting ciphers for Legacy TLS Adapter: {e}. Using system default ciphers.")

class LegacyTLSAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        # 在较新版本的 requests/urllib3 中，pool_kwargs 可能包含 ssl_context
        # 我们要确保我们的 custom_ssl_context 被使用
        if 'ssl_context' in pool_kwargs:
            del pool_kwargs['ssl_context'] # 移除，以确保我们的 context 生效

        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=custom_ssl_context,
            **pool_kwargs
        )

# --- 全局会话 ---
session = requests.Session()

def setup_authentication_and_tls():
    """
    设置 JIRA API 的 Basic Authentication 并根据配置应用 TLS 适配器。
    """
    print(f"正在为用户 {USER_EMAIL} 设置 JIRA API 认证 (使用硬编码密码)...")
    if USER_PASSWORD == "YOUR_PASSWORD_HERE" or not USER_PASSWORD:
        print("错误：请在脚本中设置 'USER_PASSWORD' 变量为您的实际密码。")
        print("出于安全考虑，脚本将退出。")
        exit()
    
    # 重置session (清除之前的所有配置)
    global session
    session = requests.Session()
    
    # 设置基本认证
    session.auth = (USER_EMAIL, USER_PASSWORD)
    
    # 添加请求头 - 基于成功的简化脚本
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "close"  # 禁用持久连接
    })
    
    # 忽略SSL警告
    if not VERIFY_SSL:
        import warnings
        warnings.filterwarnings('ignore', message='Unverified HTTPS request')
        print("Warning: SSL certificate verification is disabled!")
        
    print("认证信息已设置。")
    print("")


def test_connection():
    """
    测试与 JIRA API 的基本连接和认证。
    尝试获取当前用户信息。
    """
    print("--- 测试连接与认证 ---")
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
        
        # 从响应的cookies中获取XSRF令牌
        xsrf_token = None
        for cookie in response.cookies:
            if cookie.name == 'atlassian.xsrf.token':
                xsrf_token = cookie.value
                print(f"  已获取XSRF令牌: {xsrf_token[:10]}...")
                # 将令牌添加到session的headers中，用于后续请求
                session.headers.update({"X-Atlassian-Token": "no-check"})
                break
        
        print("连接与认证测试通过。\n")
        return True
    except requests.exceptions.Timeout:
        print(f"连接超时。请检查网络连接或服务器状态。")
    except requests.exceptions.SSLError as ssl_err:
        print(f"SSL 错误: {ssl_err}")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err}")
        print(f"响应内容: {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    except json.JSONDecodeError:
        print("错误：无法解析响应为 JSON。可能是认证失败或 URL 不正确。")
        print(f"响应内容: {response.text}")
    
    print("连接与认证测试失败。\n")
    return False

def get_issue(issue_key):
    """
    读取（获取）指定 JIRA Issue 的信息。
    """
    print(f"--- 读取 Issue: {issue_key} ---")
    api_url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_key}"
    try:
        if not VERIFY_SSL:
            warnings.filterwarnings('ignore', message='Unverified HTTPS request')
        response = session.get(api_url, verify=VERIFY_SSL)
        response.raise_for_status()
        issue_data = response.json()
        print(f"成功获取 Issue '{issue_key}' 的信息:")
        print(f"  标题 (Summary): {issue_data.get('fields', {}).get('summary')}")
        print(f"  状态 (Status): {issue_data.get('fields', {}).get('status', {}).get('name')}")
        # ... (其他字段打印)
        print(f"读取 Issue '{issue_key}' 成功。\n")
        return issue_data
    except requests.exceptions.SSLError as ssl_err:
        print(f"SSL 错误: {ssl_err}")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err} (URL: {response.url})")
        print(f"响应内容: {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    print(f"读取 Issue '{issue_key}' 失败。\n")
    return None

def create_issue(project_key, summary, description, issue_type_name):
    """
    创建（写入）一个新的 JIRA Issue。
    使用与成功的简单脚本create_form_issue.py完全相同的逻辑。
    """
    print(f"--- 创建新 Issue ---")
    
    try:
        # 重新创建会话，避免与之前的会话冲突
        create_session = requests.Session()
        create_session.auth = (USER_EMAIL, USER_PASSWORD)
        create_session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "X-Requested-With": "XMLHttpRequest"
        })
        
        # 1. 获取令牌
        print("获取必要的令牌...")
        dashboard_url = f"{JIRA_BASE_URL}/secure/Dashboard.jspa"
        dashboard_response = create_session.get(dashboard_url, verify=VERIFY_SSL)
        dashboard_response.raise_for_status()
        
        # 从Cookie中提取XSRF令牌
        xsrf_token = None
        for cookie in dashboard_response.cookies:
            if cookie.name == 'atlassian.xsrf.token':
                xsrf_token = cookie.value
                print(f"已获取XSRF令牌: {xsrf_token[:10]}...")
                break
        
        if not xsrf_token:
            print("错误: 无法获取XSRF令牌，无法创建Issue")
            return None
            
        # 访问项目页面获取其他所需信息
        project_url = f"{JIRA_BASE_URL}/browse/{project_key}"
        print(f"访问项目页面: {project_url}")
        project_response = create_session.get(project_url, verify=VERIFY_SSL)
        project_response.raise_for_status()
        
        # 2. 准备表单数据 - 与create_form_issue.py保持一致
        form_data = {
            "pid": "13904",  # 项目ID
            "issuetype": "10001",  # Issue类型ID (Story)
            "atl_token": xsrf_token,
            "summary": summary,
            "description": description,
            "fixVersions": "14613",  # 版本ID
            "isCreateIssue": "true",
            "isEditIssue": "false",
            "priority": "3",
        }
        
        # 添加额外的表单字段，完全与create_form_issue.py保持一致
        additional_fields = {
            "formToken": "",
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
        
        # 添加fieldsToRetain字段列表，与成功脚本保持一致
        fields_to_retain = [
            "project", "issuetype", "versions", "fixVersions", "components", 
            "assignee", "customfield_10005", "customfield_11302", "customfield_10006", 
            "labels", "priority", "customfield_10001", "customfield_10700", 
            "customfield_10704", "customfield_10203", "customfield_10701", "customfield_10717"
        ]
        
        # 为每个字段添加一个表单条目，使用与create_form_issue.py相同的逻辑
        form_data_with_fields = {}
        for key, value in form_data.items():
            form_data_with_fields[key] = value
        
        for field in fields_to_retain:
            form_data_with_fields[f"fieldsToRetain"] = field
        
        # 3. 创建Issue
        print(f"尝试在项目 '{project_key}' 中创建类型为 '{issue_type_name}' 的 Issue，标题为: '{summary}'")
        create_url = f"{JIRA_BASE_URL}/secure/QuickCreateIssue.jspa?decorator=none"
        
        # 配置特定的请求头，完全与create_form_issue.py保持一致
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": project_url,
            "Origin": JIRA_BASE_URL,
            "DNT": "1",
        }
        
        if not VERIFY_SSL:
            warnings.filterwarnings('ignore', message='Unverified HTTPS request')
        
        create_response = create_session.post(
            create_url,
            data=form_data_with_fields,
            headers=headers,
            verify=VERIFY_SSL
        )
        
        # 检查响应
        if create_response.status_code == 200:
            print("Issue创建成功！")
            response_text = create_response.text
            print(f"响应内容: {response_text[:200]}...")  # 截取前200字符显示
            
            # 尝试从响应中提取Issue Key
            try:
                if "issueKey" in response_text:
                    import re
                    issue_key_match = re.search(r'"issueKey":"([^"]+)"', response_text)
                    if issue_key_match:
                        new_issue_key = issue_key_match.group(1)
                        print(f"创建的Issue Key: {new_issue_key}")
                        print(f"Issue链接: {JIRA_BASE_URL}/browse/{new_issue_key}")
                        print("创建 Issue 成功。\n")
                        return new_issue_key
            except Exception as e:
                print(f"处理响应时出错: {e}")
            
            print("创建Issue可能成功，但无法提取Issue Key")
            return None
        else:
            print(f"创建失败。状态码: {create_response.status_code}")
            print(f"响应内容: {create_response.text}")
            
            if "XSRF" in create_response.text:
                print("XSRF令牌可能无效，这可能是由于令牌过期或格式不正确。")
            
            if "NullPointerException" in create_response.text:
                print("服务器发生空指针异常，可能是服务器配置问题或请求参数不正确。")
                
            print("创建 Issue 失败。\n")
            return None
        
    except requests.exceptions.SSLError as ssl_err:
        print(f"SSL 错误: {ssl_err}")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err}")
        try:
            error_json = create_response.json()
            print("错误详情:")
            if "errorMessages" in error_json: print(f"  Messages: {error_json['errorMessages']}")
            if "errors" in error_json: print(f"  Errors: {error_json['errors']}")
        except:
            try:
                print(f"  响应内容: {create_response.text}")
            except:
                print("  无法获取错误响应")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    except Exception as e:
        print(f"发生未预期错误: {e}")
    
    print("创建 Issue 失败。\n")
    return None

def search_issues(jql_query):
    """
    使用 JQL 搜索 JIRA Issues。
    """
    print(f"--- 搜索 Issues (JQL: {jql_query}) ---")
    api_url = f"{JIRA_BASE_URL}/rest/api/2/search"
    params = {"jql": jql_query, "maxResults": 5}
    try:
        if not VERIFY_SSL:
            warnings.filterwarnings('ignore', message='Unverified HTTPS request')
        response = session.get(api_url, params=params, verify=VERIFY_SSL)
        response.raise_for_status()
        search_results = response.json()
        total_issues = search_results.get('total', 0)
        issues_found = search_results.get('issues', [])
        print(f"搜索完成。总共找到 {total_issues} 个匹配的 Issue (显示前 {len(issues_found)} 个):")
        if not issues_found: print("  未找到匹配的 Issue。")
        for issue in issues_found:
            print(f"  - Key: {issue.get('key')}, 标题: {issue.get('fields', {}).get('summary')}")
        print("搜索 Issues 成功。\n")
        return search_results
    except requests.exceptions.SSLError as ssl_err:
        print(f"SSL 错误: {ssl_err}")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err} (URL: {response.url})")
        print(f"响应内容: {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    print("搜索 Issues 失败。\n")
    return None

def update_issue(issue_key, fields_to_update):
    """
    更新 JIRA Issue 的字段
    """
    print(f"--- 更新 Issue: {issue_key} ---")
    api_url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_key}"
    payload = {
        "fields": fields_to_update
    }
    try:
        if not VERIFY_SSL:
            warnings.filterwarnings('ignore', message='Unverified HTTPS request')
        print(f"尝试更新 Issue '{issue_key}' 的字段")
        response = session.put(api_url, json=payload, verify=VERIFY_SSL)
        response.raise_for_status()
        print(f"成功更新 Issue '{issue_key}' 的字段")
        print("更新 Issue 成功。\n")
        return True
    except requests.exceptions.SSLError as ssl_err:
        print(f"SSL 错误: {ssl_err}")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err} (URL: {response.url})")
        print("错误详情:")
        try:
            error_json = response.json()
            if "errorMessages" in error_json: print(f"  Messages: {error_json['errorMessages']}")
            if "errors" in error_json: print(f"  Errors: {error_json['errors']}")
        except json.JSONDecodeError: 
            print(f"  响应内容: {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    print(f"更新 Issue '{issue_key}' 失败。\n")
    return False

def add_comment(issue_key, comment_text):
    """
    向 JIRA Issue 添加评论
    
    注意: 当前存在 XSRF 验证问题，可能需要像 create_issue 函数一样使用表单提交方式
    而非直接调用 REST API
    """
    print(f"--- 向 Issue: {issue_key} 添加评论 ---")
    api_url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_key}/comment"
    payload = {
        "body": comment_text
    }
    try:
        if not VERIFY_SSL:
            warnings.filterwarnings('ignore', message='Unverified HTTPS request')
        print(f"尝试向 Issue '{issue_key}' 添加评论")
        response = session.post(api_url, json=payload, verify=VERIFY_SSL)
        response.raise_for_status()
        comment_data = response.json()
        print(f"成功添加评论，评论ID: {comment_data.get('id')}")
        print("添加评论成功。\n")
        return comment_data
    except requests.exceptions.SSLError as ssl_err:
        print(f"SSL 错误: {ssl_err}")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err} (URL: {response.url})")
        print("错误详情:")
        try:
            error_json = response.json()
            if "errorMessages" in error_json: print(f"  Messages: {error_json['errorMessages']}")
            if "errors" in error_json: print(f"  Errors: {error_json['errors']}")
        except json.JSONDecodeError: 
            print(f"  响应内容: {response.text}")
        
        if "XSRF" in response.text:
            print("  ### XSRF 验证失败: 此函数需要修改实现方式，参考 create_issue 函数的表单提交方式 ###")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    print(f"向 Issue '{issue_key}' 添加评论失败。\n")
    return None

def add_attachment(issue_key, file_path):
    """
    向 JIRA Issue 添加附件
    
    注意: 当前存在 XSRF 验证问题，可能需要像 create_issue 函数一样使用表单提交方式
    而非直接调用 REST API
    """
    print(f"--- 向 Issue: {issue_key} 添加附件 ---")
    api_url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_key}/attachments"
    
    # 需要特殊的头部，移除默认的Content-Type
    headers = session.headers.copy()
    headers.pop("Content-Type", None)
    headers["X-Atlassian-Token"] = "no-check"
    
    try:
        if not VERIFY_SSL:
            warnings.filterwarnings('ignore', message='Unverified HTTPS request')
        
            print(f"尝试向 Issue '{issue_key}' 添加附件: {file_path}")
        
        with open(file_path, 'rb') as file:
            files = {'file': (temp_file_path.split('/')[-1], file)}
            response = session.post(
                api_url, 
                headers=headers,
                files=files,
                verify=VERIFY_SSL,
                auth=session.auth
            )
        
        response.raise_for_status()
        attachment_data = response.json()
        
        if isinstance(attachment_data, list) and len(attachment_data) > 0:
            print(f"成功添加附件，附件ID: {attachment_data[0].get('id')}")
            print(f"附件名称: {attachment_data[0].get('filename')}")
        else:
            print("成功添加附件，但返回数据格式不符合预期")
            
        print("添加附件成功。\n")
        return attachment_data
    
    except FileNotFoundError:
        print(f"错误: 找不到文件 '{file_path}'")
    except requests.exceptions.SSLError as ssl_err:
        print(f"SSL 错误: {ssl_err}")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err} (URL: {response.url})")
        print("错误详情:")
        try:
            error_json = response.json()
            if "errorMessages" in error_json: print(f"  Messages: {error_json['errorMessages']}")
            if "errors" in error_json: print(f"  Errors: {error_json['errors']}")
        except json.JSONDecodeError: 
            print(f"  响应内容: {response.text}")
            
        if "XSRF" in response.text:
            print("  ### XSRF 验证失败: 此函数需要修改实现方式，参考 create_issue 函数的表单提交方式 ###")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    
    print(f"向 Issue '{issue_key}' 添加附件失败。\n")
    return None

def get_all_fields():
    """
    获取所有可用的字段信息，包括自定义字段
    """
    print("--- 获取所有字段信息 ---")
    api_url = f"{JIRA_BASE_URL}/rest/api/2/field"
    
    try:
        if not VERIFY_SSL:
            warnings.filterwarnings('ignore', message='Unverified HTTPS request')
        
        response = session.get(api_url, verify=VERIFY_SSL)
        response.raise_for_status()
        fields_data = response.json()
        
        print(f"成功获取字段信息，共 {len(fields_data)} 个字段:")
        
        # 打印系统字段
        system_fields = [field for field in fields_data if not field.get('custom', False)]
        print(f"\n系统字段 ({len(system_fields)}):")
        for field in system_fields[:5]:  # 只显示前5个，避免输出过多
            print(f"  - ID: {field.get('id')}, 名称: {field.get('name')}")
        if len(system_fields) > 5:
            print(f"  ... 等共 {len(system_fields)} 个系统字段")
            
        # 打印自定义字段
        custom_fields = [field for field in fields_data if field.get('custom', False)]
        print(f"\n自定义字段 ({len(custom_fields)}):")
        for field in custom_fields[:5]:  # 只显示前5个，避免输出过多
            print(f"  - ID: {field.get('id')}, 名称: {field.get('name')}")
        if len(custom_fields) > 5:
            print(f"  ... 等共 {len(custom_fields)} 个自定义字段")
            
        print("\n获取字段信息成功。\n")
        return fields_data
    
    except requests.exceptions.SSLError as ssl_err:
        print(f"SSL 错误: {ssl_err}")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err} (URL: {response.url})")
        print(f"响应内容: {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    
    print("获取字段信息失败。\n")
    return None

def get_issue_types():
    """
    获取所有可用的Issue类型
    """
    print("--- 获取Issue类型 ---")
    api_url = f"{JIRA_BASE_URL}/rest/api/2/issuetype"
    
    try:
        if not VERIFY_SSL:
            warnings.filterwarnings('ignore', message='Unverified HTTPS request')
        
        response = session.get(api_url, verify=VERIFY_SSL)
        response.raise_for_status()
        issue_types_data = response.json()
        
        print(f"成功获取Issue类型，共 {len(issue_types_data)} 个类型:")
        for issue_type in issue_types_data:
            print(f"  - ID: {issue_type.get('id')}, 名称: {issue_type.get('name')}")
            
        print("\n获取Issue类型成功。\n")
        return issue_types_data
    
    except requests.exceptions.SSLError as ssl_err:
        print(f"SSL 错误: {ssl_err}")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误: {http_err} (URL: {response.url})")
        print(f"响应内容: {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
    
    print("获取Issue类型失败。\n")
    return None

if __name__ == "__main__":
    print("JIRA API 读写测试脚本")
    print("=====================\n")

    # 1. 设置认证和 TLS 适配器 (如果启用)
    setup_authentication_and_tls()

    # 2. 测试连接和认证
    if not test_connection():
        print("无法连接到 JIRA 或认证失败。请检查 JIRA URL、邮箱、密码以及网络连接。")
        # 提示已在 test_connection() 内部处理
        exit()

    # 3. 创建一个新的 Issue (写测试)
    new_issue_summary = "API 测试 - 新建任务 (密码认证)"
    new_issue_description = "这是一个通过 Python 脚本自动创建的测试任务 (使用密码认证)。\n用于验证 JIRA API 的写入功能。"
    created_issue_key = create_issue(
        project_key=TEST_PROJECT_KEY,
        summary=new_issue_summary,
        description=new_issue_description,
        issue_type_name=TEST_ISSUE_TYPE_NAME
    )

    # 4. 读取刚创建的 Issue (读测试)
    if created_issue_key:
        get_issue(created_issue_key)
        
        # 5. 向刚创建的Issue添加评论 (新功能测试)
        add_comment(
            issue_key=created_issue_key,
            comment_text="这是一条通过API添加的测试评论。用于验证评论功能。"
        )
        
        # 6. 更新刚创建的Issue (新功能测试)
        update_issue(
            issue_key=created_issue_key,
            fields_to_update={
                "summary": f"{new_issue_summary} - 已更新",
                "description": f"{new_issue_description}\n\n此描述已通过API更新。"
            }
        )
        
        # 7. 尝试添加附件 (新功能测试)
        try:
            # 创建一个临时文件作为测试附件
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp:
                temp.write("这是一个测试附件内容，用于验证JIRA API的附件上传功能。".encode('utf-8'))
                temp_file_path = temp.name
            
            print(f"创建临时测试文件: {temp_file_path}")
            
            # 上传附件
            add_attachment(
                issue_key=created_issue_key,
                file_path=temp_file_path
            )
            
            # 删除临时文件
            os.unlink(temp_file_path)
            print(f"已删除临时测试文件: {temp_file_path}")
        except Exception as e:
            print(f"附件测试过程中发生错误: {e}")
            
    else:
        print("由于上一步创建 Issue 失败，跳过后续的读取、更新、评论和附件测试。\n")

    # 8. 获取字段信息 (新功能测试)
    get_all_fields()
    
    # 9. 获取Issue类型 (新功能测试)
    get_issue_types()
    
    # 10. 读取一个已知的 Issue (读测试)
    known_issue_key_default = f"{TEST_PROJECT_KEY}-1" 
    user_input_known_issue = input(f"请输入一个您项目中已知的 Issue Key 进行读取测试 (例如 {known_issue_key_default}，直接回车使用此默认值): ").strip()
    known_issue_key_to_test = user_input_known_issue if user_input_known_issue else known_issue_key_default
    get_issue(known_issue_key_to_test)
    
    # 11. 使用 JQL 搜索 Issues (读测试)
    jql_query_example = f"project = {TEST_PROJECT_KEY} AND issuetype = {TEST_ISSUE_TYPE_NAME} ORDER BY created DESC"
    search_issues(jql_query_example)

    print("--- JIRA API 测试完成 ---")

