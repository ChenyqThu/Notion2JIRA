#!/bin/bash

# Notion2JIRA 内网同步服务启动脚本

set -e

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# 检查Python环境
check_python() {
    log_info "检查Python环境..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_info "Python版本: $PYTHON_VERSION"
    
    # 检查Python版本是否 >= 3.8
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        log_error "Python版本必须 >= 3.8"
        exit 1
    fi
}

# 检查并创建虚拟环境
setup_venv() {
    log_info "设置Python虚拟环境..."
    
    VENV_DIR="$SCRIPT_DIR/venv"
    
    if [ ! -d "$VENV_DIR" ]; then
        log_info "创建虚拟环境..."
        python3 -m venv "$VENV_DIR"
    fi
    
    log_info "激活虚拟环境..."
    source "$VENV_DIR/bin/activate"
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装依赖
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        log_info "安装Python依赖..."
        pip install -r "$SCRIPT_DIR/requirements.txt"
    else
        log_warn "未找到requirements.txt文件"
    fi
}

# 检查环境变量
check_env() {
    log_info "检查环境变量..."
    
    ENV_FILE="$PROJECT_ROOT/.env"
    if [ ! -f "$ENV_FILE" ]; then
        log_error "未找到.env文件: $ENV_FILE"
        log_info "请参考.env_example创建.env文件"
        exit 1
    fi
    
    # 检查必要的环境变量
    source "$ENV_FILE"
    
    REQUIRED_VARS=(
        "JIRA_BASE_URL"
        "JIRA_USERNAME" 
        "JIRA_PASSWORD"
        "NOTION_TOKEN"
        "NOTION_DATABASE_ID"
    )
    
    # 可选但重要的环境变量
    OPTIONAL_VARS=(
        "REDIS_HOST"
        "REDIS_PORT"
        "REDIS_PASSWORD"
        "REDIS_DB"
        "SYNC_QUEUE_NAME"
        "LOG_LEVEL"
    )
    
    # 检查必要变量
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "缺少必要的环境变量: $var"
            exit 1
        fi
    done
    
    # 检查可选变量并给出提示
    for var in "${OPTIONAL_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            case $var in
                "REDIS_PASSWORD")
                    log_debug "Redis密码未设置，将使用无密码连接"
                    ;;
                "REDIS_HOST")
                    log_debug "Redis主机未设置，将使用默认值: localhost"
                    ;;
                "REDIS_PORT")
                    log_debug "Redis端口未设置，将使用默认值: 6379"
                    ;;
                *)
                    log_debug "可选环境变量 $var 未设置，将使用默认值"
                    ;;
            esac
        else
            case $var in
                "REDIS_PASSWORD")
                    log_debug "Redis密码已设置"
                    ;;
                *)
                    log_debug "$var = ${!var}"
                    ;;
            esac
        fi
    done
    
    log_info "环境变量检查通过"
}

# 检查Redis连接
check_redis() {
    log_info "检查Redis连接..."
    
    REDIS_HOST="${REDIS_HOST:-localhost}"
    REDIS_PORT="${REDIS_PORT:-6379}"
    REDIS_PASSWORD="${REDIS_PASSWORD:-}"
    
    if command -v redis-cli &> /dev/null; then
        # 构建redis-cli命令
        REDIS_CMD="redis-cli -h $REDIS_HOST -p $REDIS_PORT"
        
        # 如果有密码，添加密码参数
        if [ -n "$REDIS_PASSWORD" ]; then
            REDIS_CMD="$REDIS_CMD -a $REDIS_PASSWORD"
            log_debug "使用密码连接Redis"
        else
            log_debug "无密码连接Redis"
        fi
        
        # 测试连接
        if $REDIS_CMD ping > /dev/null 2>&1; then
            log_info "Redis连接正常 ($REDIS_HOST:$REDIS_PORT)"
        else
            log_error "Redis连接失败 ($REDIS_HOST:$REDIS_PORT)"
            if [ -n "$REDIS_PASSWORD" ]; then
                log_error "请检查Redis密码是否正确"
            else
                log_error "请检查Redis是否需要密码验证"
            fi
            log_info "请确保Redis服务正在运行且配置正确"
            exit 1
        fi
    else
        log_warn "redis-cli未安装，跳过Redis连接检查"
        log_info "建议安装redis-cli以验证Redis连接"
    fi
}

# 创建必要的目录
create_dirs() {
    log_info "创建必要的目录..."
    
    DIRS=(
        "$SCRIPT_DIR/logs"
        "$SCRIPT_DIR/data"
        "$SCRIPT_DIR/tmp"
    )
    
    for dir in "${DIRS[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_debug "创建目录: $dir"
        fi
    done
}

# 启动服务
start_service() {
    log_info "启动内网同步服务..."
    
    cd "$SCRIPT_DIR"
    
    # 激活虚拟环境
    source "$SCRIPT_DIR/venv/bin/activate"
    
    # 设置Python路径
    export PYTHONPATH="$SCRIPT_DIR:$PROJECT_ROOT:$PYTHONPATH"
    
    # 启动服务
    python3 main.py
}

# 显示帮助信息
show_help() {
    echo "Notion2JIRA 内网同步服务启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  -c, --check    仅执行环境检查，不启动服务"
    echo "  -v, --verbose  详细输出"
    echo "  --setup-only   仅设置环境，不启动服务"
    echo ""
    echo "示例:"
    echo "  $0              # 启动服务"
    echo "  $0 --check     # 检查环境"
    echo "  $0 --setup-only # 仅设置环境"
}

# 主函数
main() {
    local check_only=false
    local setup_only=false
    local verbose=false
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -c|--check)
                check_only=true
                shift
                ;;
            --setup-only)
                setup_only=true
                shift
                ;;
            -v|--verbose)
                verbose=true
                set -x
                shift
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    log_info "=== Notion2JIRA 内网同步服务 ==="
    log_info "项目目录: $PROJECT_ROOT"
    log_info "服务目录: $SCRIPT_DIR"
    echo ""
    
    # 执行检查
    check_python
    check_env
    check_redis
    create_dirs
    
    if [ "$check_only" = true ]; then
        log_info "环境检查完成，所有检查通过"
        exit 0
    fi
    
    # 设置环境
    setup_venv
    
    if [ "$setup_only" = true ]; then
        log_info "环境设置完成"
        exit 0
    fi
    
    # 启动服务
    start_service
}

# 错误处理
trap 'log_error "脚本执行失败，退出码: $?"' ERR

# 执行主函数
main "$@" 