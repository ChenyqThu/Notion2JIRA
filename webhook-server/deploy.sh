#!/bin/bash

# Notion Webhook Server 部署脚本
# 用于在服务器上部署 webhook 服务

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
APP_NAME="notion-webhook"
APP_DIR="/opt/notion2jira/webhook-server"
SERVICE_USER="webhook"
NGINX_SITE="notion2jira.chenge.ink"
DOMAIN="notion2jira.chenge.ink"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为 root 用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要 root 权限运行"
        exit 1
    fi
}

# 安装系统依赖
install_dependencies() {
    log_info "安装系统依赖..."
    
    # 更新包管理器
    apt update
    
    # 安装必要的包
    apt install -y curl wget gnupg2 software-properties-common nginx redis-server
    
    # 安装 Node.js 16.x
    curl -fsSL https://deb.nodesource.com/setup_16.x | bash -
    apt install -y nodejs
    
    # 安装 PM2
    npm install -g pm2
    
    log_success "系统依赖安装完成"
}

# 创建应用用户
create_user() {
    log_info "创建应用用户..."
    
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd -r -s /bin/bash -d /home/$SERVICE_USER -m $SERVICE_USER
        log_success "用户 $SERVICE_USER 创建成功"
    else
        log_warning "用户 $SERVICE_USER 已存在"
    fi
}

# 创建应用目录
setup_directories() {
    log_info "设置应用目录..."
    
    mkdir -p $APP_DIR
    mkdir -p $APP_DIR/logs
    mkdir -p /etc/ssl/certs
    mkdir -p /etc/ssl/private
    
    chown -R $SERVICE_USER:$SERVICE_USER $APP_DIR
    chmod 755 $APP_DIR
    chmod 755 $APP_DIR/logs
    
    log_success "目录设置完成"
}

# 部署应用代码
deploy_app() {
    log_info "部署应用代码..."
    
    # 复制文件到应用目录
    cp -r ./* $APP_DIR/
    
    # 设置权限
    chown -R $SERVICE_USER:$SERVICE_USER $APP_DIR
    chmod +x $APP_DIR/scripts/*.js
    
    # 安装依赖
    cd $APP_DIR
    sudo -u $SERVICE_USER npm install --production
    
    log_success "应用代码部署完成"
}

# 配置环境变量
setup_environment() {
    log_info "配置环境变量..."
    
    if [[ ! -f "$APP_DIR/.env" ]]; then
        cp $APP_DIR/env.example $APP_DIR/.env
        
        # 生成随机的 API Key
        ADMIN_API_KEY=$(openssl rand -hex 32)
        
        # 更新配置文件
        sed -i "s/your_secure_admin_api_key_here/$ADMIN_API_KEY/" $APP_DIR/.env
        sed -i "s/localhost/127.0.0.1/" $APP_DIR/.env
        
        log_warning "请编辑 $APP_DIR/.env 文件，设置正确的配置参数"
        log_warning "生成的管理 API Key: $ADMIN_API_KEY"
    else
        log_warning "环境配置文件已存在，跳过创建"
    fi
    
    chown $SERVICE_USER:$SERVICE_USER $APP_DIR/.env
    chmod 600 $APP_DIR/.env
}

# 配置 Redis
setup_redis() {
    log_info "配置 Redis..."
    
    # 启动并启用 Redis 服务
    systemctl start redis-server
    systemctl enable redis-server
    
    # 生成 Redis 密码
    REDIS_PASSWORD=$(openssl rand -base64 32)
    
    # 配置 Redis 安全设置
    cat >> /etc/redis/redis.conf << EOF

# 安全配置
bind 0.0.0.0
protected-mode yes
requirepass $REDIS_PASSWORD
maxmemory 256mb
maxmemory-policy allkeys-lru

# 日志配置
loglevel notice
logfile /var/log/redis/redis-server.log
EOF
    
    # 更新环境变量中的 Redis 密码
    sed -i "s/your_redis_password/$REDIS_PASSWORD/" $APP_DIR/.env
    
    # 重启 Redis 服务
    systemctl restart redis-server
    
    log_success "Redis 配置完成"
    log_warning "Redis 密码: $REDIS_PASSWORD"
    log_warning "请将此密码配置到内网同步服务中"
}

# 配置 Nginx
setup_nginx() {
    log_info "配置 Nginx..."
    
    # 复制 Nginx 配置
    cp $APP_DIR/nginx.conf /etc/nginx/sites-available/$NGINX_SITE
    
    # 启用站点
    ln -sf /etc/nginx/sites-available/$NGINX_SITE /etc/nginx/sites-enabled/
    
    # 删除默认站点（如果存在）
    rm -f /etc/nginx/sites-enabled/default
    
    # 测试配置
    nginx -t
    
    log_success "Nginx 配置完成"
    log_warning "请确保 SSL 证书已正确配置在 /etc/ssl/certs/ 和 /etc/ssl/private/"
}

# 配置 PM2
setup_pm2() {
    log_info "配置 PM2..."
    
    cd $APP_DIR
    
    # 使用应用用户启动 PM2
    sudo -u $SERVICE_USER pm2 start ecosystem.config.js --env production
    sudo -u $SERVICE_USER pm2 save
    
    # 设置开机自启
    pm2 startup systemd -u $SERVICE_USER --hp /home/$SERVICE_USER
    
    log_success "PM2 配置完成"
}

# 配置防火墙
setup_firewall() {
    log_info "配置防火墙..."
    
    if command -v ufw &> /dev/null; then
        # 基础端口
        ufw allow 22/tcp
        ufw allow 80/tcp
        ufw allow 443/tcp
        
        # Redis 端口 - 仅允许内网访问
        # 注意：请根据实际内网 IP 段修改
        ufw allow from 10.0.0.0/8 to any port 6379
        ufw allow from 172.16.0.0/12 to any port 6379
        ufw allow from 192.168.0.0/16 to any port 6379
        
        ufw --force enable
        log_success "UFW 防火墙配置完成"
        log_warning "Redis 端口 6379 已开放给内网访问"
        log_warning "如需限制特定 IP，请手动配置：ufw allow from <内网服务器IP> to any port 6379"
    else
        log_warning "UFW 未安装，请手动配置防火墙"
        log_warning "需要开放端口：22, 80, 443, 6379(仅内网)"
    fi
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 启动 Nginx
    systemctl start nginx
    systemctl enable nginx
    
    # 重启 Redis（确保配置生效）
    systemctl restart redis-server
    
    log_success "服务启动完成"
}

# 验证部署
verify_deployment() {
    log_info "验证部署..."
    
    # 检查服务状态
    if systemctl is-active --quiet nginx; then
        log_success "Nginx 运行正常"
    else
        log_error "Nginx 未运行"
    fi
    
    if systemctl is-active --quiet redis-server; then
        log_success "Redis 运行正常"
    else
        log_error "Redis 未运行"
    fi
    
    # 检查应用是否运行
    if sudo -u $SERVICE_USER pm2 list | grep -q $APP_NAME; then
        log_success "应用运行正常"
    else
        log_error "应用未运行"
    fi
    
    # 测试健康检查
    sleep 5
    if curl -f http://localhost:7654/health > /dev/null 2>&1; then
        log_success "应用健康检查通过"
    else
        log_warning "应用健康检查失败，请检查日志"
    fi

    # 1. 检查端口占用
    sudo netstat -tlnp | grep :7654
    sudo netstat -tlnp | grep :443
}

# 显示部署信息
show_deployment_info() {
    log_info "部署完成！"
    echo ""
    echo "=== 部署信息 ==="
    echo "应用目录: $APP_DIR"
    echo "服务用户: $SERVICE_USER"
    echo "域名: $DOMAIN"
    echo "本地端口: 7654"
    echo ""
    echo "=== 管理命令 ==="
    echo "查看应用状态: sudo -u $SERVICE_USER pm2 status"
    echo "查看应用日志: sudo -u $SERVICE_USER pm2 logs $APP_NAME"
    echo "重启应用: sudo -u $SERVICE_USER pm2 restart $APP_NAME"
    echo "查看 Nginx 状态: systemctl status nginx"
    echo "查看 Redis 状态: systemctl status redis-server"
    echo ""
    echo "=== 重要提醒 ==="
    echo "1. 请配置 SSL 证书到 /etc/ssl/certs/ 和 /etc/ssl/private/"
    echo "2. 请编辑 $APP_DIR/.env 文件设置正确的配置"
    echo "3. 请确保域名 DNS 解析指向此服务器"
    echo "4. 管理 API Key 已保存在 .env 文件中"
    echo ""
}

# 主函数
main() {
    log_info "开始部署 Notion Webhook Server..."
    
    check_root
    install_dependencies
    create_user
    setup_directories
    deploy_app
    setup_environment
    setup_redis
    setup_nginx
    setup_pm2
    setup_firewall
    start_services
    verify_deployment
    show_deployment_info
    
    log_success "部署完成！"
}

# 运行主函数
main "$@" 