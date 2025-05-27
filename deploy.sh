#!/bin/bash

# Notion2JIRA 系统一键部署脚本

set -e

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# 显示横幅
show_banner() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    Notion2JIRA 系统部署                      ║"
    echo "║                                                              ║"
    echo "║  这个脚本将部署完整的 Notion2JIRA 同步系统                    ║"
    echo "║  包括公网代理服务和内网同步服务                               ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
}

# 检查系统要求
check_requirements() {
    log_info "检查系统要求..."
    
    # 检查操作系统
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        log_warn "当前系统不是Linux，部分功能可能不可用"
    fi
    
    # 检查Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js 未安装，请先安装 Node.js 16+"
        exit 1
    fi
    
    NODE_VERSION=$(node --version | cut -d'v' -f2)
    log_info "Node.js 版本: $NODE_VERSION"
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装，请先安装 Python 3.8+"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_info "Python 版本: $PYTHON_VERSION"
    
    # 检查Redis
    if ! command -v redis-server &> /dev/null; then
        log_warn "Redis 未安装，请确保Redis服务可用"
    else
        REDIS_VERSION=$(redis-server --version | head -n1 | cut -d' ' -f3)
        log_info "Redis 版本: $REDIS_VERSION"
    fi
    
    # 检查PM2
    if ! command -v pm2 &> /dev/null; then
        log_info "安装 PM2 进程管理器..."
        npm install -g pm2
    fi
    
    log_info "系统要求检查完成"
}

# 检查环境变量
check_environment() {
    log_info "检查环境配置..."
    
    ENV_FILE="$SCRIPT_DIR/.env"
    if [ ! -f "$ENV_FILE" ]; then
        log_error "未找到 .env 文件"
        log_info "请复制 .env_example 并配置必要的环境变量"
        
        if [ -f "$SCRIPT_DIR/.env_example" ]; then
            log_info "正在复制 .env_example 到 .env..."
            cp "$SCRIPT_DIR/.env_example" "$ENV_FILE"
            log_warn "请编辑 .env 文件并配置以下必要变量："
            echo "  - JIRA_BASE_URL"
            echo "  - JIRA_USERNAME"
            echo "  - JIRA_PASSWORD"
            echo "  - NOTION_TOKEN"
            echo "  - NOTION_DATABASE_ID"
            exit 1
        else
            log_error "未找到 .env_example 文件"
            exit 1
        fi
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
    
    missing_vars=()
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "缺少必要的环境变量:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        log_info "请编辑 .env 文件并配置这些变量"
        exit 1
    fi
    
    log_info "环境配置检查通过"
}

# 部署公网代理服务
deploy_webhook_server() {
    log_info "部署公网代理服务..."
    
    cd "$SCRIPT_DIR/webhook-server"
    
    # 安装依赖
    if [ -f "package.json" ]; then
        log_info "安装 Node.js 依赖..."
        npm install
    else
        log_error "未找到 package.json 文件"
        exit 1
    fi
    
    # 检查配置文件
    if [ ! -f "ecosystem.config.js" ]; then
        log_error "未找到 PM2 配置文件"
        exit 1
    fi
    
    log_info "公网代理服务部署完成"
}

# 部署内网同步服务
deploy_sync_service() {
    log_info "部署内网同步服务..."
    
    cd "$SCRIPT_DIR/sync-service"
    
    # 运行设置脚本
    if [ -f "start.sh" ]; then
        log_info "设置 Python 环境..."
        chmod +x start.sh
        ./start.sh --setup-only
    else
        log_error "未找到启动脚本"
        exit 1
    fi
    
    log_info "内网同步服务部署完成"
}

# 启动服务
start_services() {
    log_info "启动系统服务..."
    
    # 启动公网代理服务
    log_info "启动公网代理服务..."
    cd "$SCRIPT_DIR/webhook-server"
    pm2 start ecosystem.config.js
    
    # 启动内网同步服务
    log_info "启动内网同步服务..."
    cd "$SCRIPT_DIR/sync-service"
    
    # 创建PM2配置文件
    cat > sync-service.config.js << EOF
module.exports = {
  apps: [{
    name: 'notion2jira-sync',
    script: 'main.py',
    interpreter: './venv/bin/python',
    cwd: '$SCRIPT_DIR/sync-service',
    env: {
      PYTHONPATH: '$SCRIPT_DIR/sync-service:$SCRIPT_DIR'
    },
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    log_file: './logs/pm2.log',
    out_file: './logs/pm2-out.log',
    error_file: './logs/pm2-error.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
  }]
};
EOF
    
    pm2 start sync-service.config.js
    
    log_info "系统服务启动完成"
}

# 检查服务状态
check_services() {
    log_info "检查服务状态..."
    
    # 显示PM2状态
    pm2 status
    
    # 检查端口占用
    WEBHOOK_PORT=${PORT:-3000}
    if netstat -tuln | grep ":$WEBHOOK_PORT " > /dev/null; then
        log_info "公网代理服务正在端口 $WEBHOOK_PORT 运行"
    else
        log_warn "公网代理服务可能未正常启动"
    fi
    
    # 检查日志
    log_info "最近的服务日志:"
    echo "--- 公网代理服务日志 ---"
    pm2 logs notion-webhook-server --lines 5 --nostream || true
    
    echo "--- 内网同步服务日志 ---"
    pm2 logs notion2jira-sync --lines 5 --nostream || true
}

# 运行测试
run_tests() {
    log_info "运行基础测试..."
    
    # 测试内网同步服务
    cd "$SCRIPT_DIR/sync-service"
    if [ -f "test_basic.py" ]; then
        log_info "运行内网同步服务测试..."
        source venv/bin/activate
        python test_basic.py
    else
        log_warn "未找到测试文件，跳过测试"
    fi
}

# 显示部署信息
show_deployment_info() {
    log_info "部署完成！"
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                        部署信息                              ║"
    echo "╠══════════════════════════════════════════════════════════════╣"
    echo "║ 公网代理服务:                                                 ║"
    echo "║   - 端口: ${PORT:-3000}                                      ║"
    echo "║   - Webhook URL: https://notion2jira.tp-link.com/webhook/notion ║"
    echo "║   - 健康检查: https://notion2jira.tp-link.com/health         ║"
    echo "║                                                              ║"
    echo "║ 内网同步服务:                                                 ║"
    echo "║   - 状态: 运行中                                              ║"
    echo "║   - 日志: sync-service/logs/sync_service.log                 ║"
    echo "║                                                              ║"
    echo "║ 管理命令:                                                     ║"
    echo "║   - 查看状态: pm2 status                                     ║"
    echo "║   - 查看日志: pm2 logs                                       ║"
    echo "║   - 重启服务: pm2 restart all                               ║"
    echo "║   - 停止服务: pm2 stop all                                  ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    
    log_info "接下来的步骤:"
    echo "1. 在 Notion 中配置 Webhook URL"
    echo "2. 测试同步功能"
    echo "3. 监控服务日志"
    echo ""
    log_info "如有问题，请查看日志文件或运行 pm2 logs"
}

# 显示帮助信息
show_help() {
    echo "Notion2JIRA 系统部署脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help          显示帮助信息"
    echo "  -c, --check-only    仅检查环境，不执行部署"
    echo "  -s, --start-only    仅启动服务（假设已部署）"
    echo "  -t, --test-only     仅运行测试"
    echo "  --no-tests          跳过测试"
    echo "  --no-start          部署但不启动服务"
    echo ""
    echo "示例:"
    echo "  $0                  # 完整部署"
    echo "  $0 --check-only     # 仅检查环境"
    echo "  $0 --start-only     # 仅启动服务"
}

# 主函数
main() {
    local check_only=false
    local start_only=false
    local test_only=false
    local no_tests=false
    local no_start=false
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -c|--check-only)
                check_only=true
                shift
                ;;
            -s|--start-only)
                start_only=true
                shift
                ;;
            -t|--test-only)
                test_only=true
                shift
                ;;
            --no-tests)
                no_tests=true
                shift
                ;;
            --no-start)
                no_start=true
                shift
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    show_banner
    
    # 检查环境
    check_requirements
    check_environment
    
    if [ "$check_only" = true ]; then
        log_info "环境检查完成，系统满足部署要求"
        exit 0
    fi
    
    if [ "$test_only" = true ]; then
        run_tests
        exit 0
    fi
    
    if [ "$start_only" = true ]; then
        start_services
        check_services
        show_deployment_info
        exit 0
    fi
    
    # 执行部署
    deploy_webhook_server
    deploy_sync_service
    
    # 运行测试
    if [ "$no_tests" != true ]; then
        run_tests
    fi
    
    # 启动服务
    if [ "$no_start" != true ]; then
        start_services
        sleep 3  # 等待服务启动
        check_services
    fi
    
    show_deployment_info
}

# 错误处理
trap 'log_error "部署脚本执行失败，退出码: $?"' ERR

# 执行主函数
main "$@" 