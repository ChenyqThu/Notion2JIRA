# Notion2JIRA 同步系统

## 项目简介

Notion2JIRA 是一个自动化同步系统，实现 Notion Database 与 JIRA 项目之间的数据同步。该系统专为 EBG 商用产品团队设计，解决需求管理和开发管理系统之间的数据孤岛问题。

## 核心功能

- **双向同步**: Notion ↔ JIRA 自动双向同步
- **字段映射**: 智能的字段映射和数据转换
- **状态回写**: 同步完成后自动更新Notion状态和JIRA链接
- **增量检测**: 基于时间戳的增量同步机制
- **重复检测**: 防止重复创建 JIRA Issue
- **错误处理**: 完善的错误处理和重试机制

## 项目状态

- ✅ **第0阶段**: 项目调研与准备（已完成 100%）
- ✅ **第1阶段**: 基础设施搭建（已完成 100%）
- 🔄 **第2阶段**: 核心同步功能开发（进行中 20%）
- 📋 **第3阶段**: 反向同步功能开发（待开始）
- 📋 **第4阶段**: 测试与部署（待开始）

### 最新进展
- ✅ 公网代理服务（Webhook接收）
- ✅ 内网同步服务架构
- ✅ Redis消息队列集成
- ✅ 配置管理和日志系统
- ✅ 系统监控和健康检查
- ✅ 一键部署脚本
- 🔄 字段映射引擎开发中
- 🔄 JIRA Issue创建逻辑开发中

## 核心文档

### 📋 [PRD.md](./PRD.md) - 产品需求文档
- 项目背景与目标
- 功能需求清单
- 字段映射规范
- 验收标准

### 🏗️ [Architecture.md](./Architecture.md) - 架构设计文档
- 系统架构设计
- 核心模块设计
- 部署架构
- 安全架构
- 性能优化

### 📝 [tasks.md](./tasks.md) - 任务分解文档
- 详细任务分解
- 分阶段实施计划
- 进度跟踪
- 风险管理

## 快速开始

### 当前已完成的工作
```bash
# 服务器环境准备
# - CentOS 7 云服务器
# - 域名 https://notion2jira.tp-link.com 
# - SSL证书和Nginx配置

# JIRA API测试和字段映射分析
python field_mapping_analyzer.py  # 字段映射分析
python test_rest_api.py          # JIRA API完整测试

# Notion webhook接口测试
# - 已完成webhook数据格式分析
# - 已了解接口调用方式
```

### 环境配置
```bash
# 复制环境变量模板
cp .env_example .env

# 编辑配置文件
vim .env
```

### 依赖安装
```bash
pip install -r requirements.txt
```

## 技术栈

- **公网代理**: Node.js + Express + Redis
- **内网服务**: Python + FastAPI + Redis
- **部署**: Docker + Nginx + PM2
- **监控**: 自定义监控面板

## 项目结构

```
Notion2JIRA/
├── PRD.md                          # 产品需求文档
├── Architecture.md                 # 架构设计文档
├── tasks.md                        # 任务分解文档
├── webhook-server/                 # 公网代理服务
├── field_mapping_analyzer.py       # 字段映射分析工具
├── test_rest_api.py               # JIRA API测试脚本
└── requirements.txt               # Python依赖
```

## 联系方式

- **项目负责人**: 产品团队
- **技术负责人**: 开发团队
- **问题反馈**: 通过 JIRA 或团队群组

## 许可证

内部项目，仅供 EBG 商用产品团队使用。 