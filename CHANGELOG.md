# Notion2JIRA 变更日志

本文档记录了 Notion2JIRA 项目的所有重要变更和版本更新。

## [v1.3.0] - 2025-12-26

### 🎉 重大改进

#### 字段存储策略优化
- **新增**: 双重存储结构（properties + raw_properties）
- **新增**: 支持 32 种字段类型解析，包括新发现的 formula、verification 等
- **改进**: 智能字段类型检测和处理机制
- **改进**: 容错机制，解析失败时保留原始数据
- **新增**: 扩展字段类型支持（email, phone_number, url, unique_id, verification）

#### 同步触发机制重构
- **移除**: Formula 字段依赖，简化触发逻辑
- **新增**: Button Property 点击检测（推荐方式）
- **新增**: Checkbox 控制支持（sync2jira、同步到JIRA、Sync to JIRA）
- **新增**: 默认同步策略（收到 webhook 即同步）
- **改进**: 灵活的触发条件配置

#### CORS 配置优化
- **新增**: CORS_ENABLED 环境变量开关
- **改进**: 开发环境自动允许所有来源
- **改进**: 生产环境可严格控制允许的来源
- **新增**: 环境适配的 CORS 策略

### 🔧 技术改进

#### Webhook 数据处理
- **修复**: 中间件冲突问题（stream encoding 错误）
- **改进**: 原始请求体捕获机制
- **改进**: 错误处理和日志记录
- **提升**: 数据解析准确性和系统稳定性

#### 部署配置优化
- **移除**: deploy.sh 一键部署脚本
- **新增**: 详细的手动部署指南
- **改进**: 端口配置标准化（统一使用 7654）
- **新增**: Docker Compose 部署配置
- **新增**: 本地开发环境指南

#### 监控和调试
- **新增**: 健康检查接口 (/health)
- **新增**: 统计信息接口 (/stats)
- **新增**: 队列状态接口 (/queue/status)
- **改进**: 结构化日志记录
- **新增**: 多种调试和监控方法

### 📝 文档更新
- **更新**: README.md 全面重写，包含详细部署指南
- **更新**: tasks.md 反映当前项目进展
- **新增**: CHANGELOG.md 变更日志
- **改进**: 环境配置说明和常见问题解答

### 🐛 问题修复
- **修复**: Redis 认证配置问题
- **修复**: 中间件流冲突导致的服务器错误
- **修复**: 端口配置不一致问题
- **修复**: .gitignore 配置不完整问题

---

## [v1.2.0] - 2025-12-25

### 🚀 新功能
- **新增**: 移除 Formula 字段依赖的同步触发机制
- **新增**: 支持多种同步触发方式（Button、Checkbox、默认）
- **改进**: 字段解析逻辑，支持更多字段类型

### 🔧 技术改进
- **优化**: Webhook 数据接收和处理流程
- **改进**: 错误处理机制
- **新增**: 字段数量统计和日志记录

### 📝 文档
- **更新**: 同步触发机制说明
- **新增**: 字段类型支持列表

---

## [v1.1.0] - 2025-12-24

### 🎉 重大功能
- **新增**: 增强的字段存储策略
- **新增**: CORS 配置优化
- **改进**: 环境变量管理

### 🔧 技术改进
- **新增**: 双重存储结构设计
- **改进**: 字段类型检测和处理
- **新增**: 开发/生产环境 CORS 适配

### 🐛 问题修复
- **修复**: 字段解析错误
- **修复**: 环境配置问题

---

## [v1.0.0] - 2025-12-23

### 🎉 首次发布
- **新增**: 基础 Webhook 服务
- **新增**: Redis 消息队列集成
- **新增**: 基础字段解析功能
- **新增**: Express.js 服务器框架
- **新增**: PM2 进程管理配置

### 🔧 核心功能
- **实现**: Notion webhook 接收
- **实现**: 基础字段数据解析
- **实现**: Redis 队列消息推送
- **实现**: 基础错误处理

### 📝 文档
- **创建**: 项目基础文档
- **创建**: 部署配置文件
- **创建**: 环境变量模板

---

## 版本规划

### 🔮 即将发布

#### [v1.4.0] - 计划 2025-12-30
- **目标**: 完成 JIRA Issue 创建功能
- **新增**: JiraClient 类实现
- **新增**: Issue 创建 API 调用
- **新增**: 重复检测机制
- **新增**: Notion 回写功能

#### [v2.0.0] - 计划 2025-01-15
- **目标**: 双向同步功能
- **新增**: JIRA → Notion 反向同步
- **新增**: 定时任务调度器
- **新增**: 冲突检测和处理
- **新增**: 完整的监控面板

### 🎯 长期规划

#### [v2.1.0] - 计划 2025-02-01
- **新增**: 批量同步功能
- **新增**: 高级配置管理
- **改进**: 性能优化
- **新增**: 用户界面

#### [v3.0.0] - 计划 2025-03-01
- **重构**: 微服务架构
- **新增**: 多项目支持
- **新增**: 插件系统
- **改进**: 企业级功能

---

## 贡献指南

### 版本号规则
- **主版本号**: 重大架构变更或不兼容更新
- **次版本号**: 新功能添加或重要改进
- **修订版本号**: 问题修复和小改进

### 变更类型
- 🎉 **重大改进**: 新功能或重要特性
- 🔧 **技术改进**: 代码优化和技术升级
- 🐛 **问题修复**: Bug 修复
- 📝 **文档更新**: 文档改进
- 🚀 **新功能**: 功能添加
- ⚡ **性能优化**: 性能提升
- 🔒 **安全更新**: 安全相关改进

### 提交规范
```
类型(范围): 简短描述

详细描述（可选）

相关问题: #123
```

---

## 支持和反馈

如果您在使用过程中遇到问题或有改进建议，请通过以下方式联系我们：

- **问题报告**: 通过 JIRA 创建 Issue
- **功能建议**: 团队群组讨论
- **技术支持**: 联系开发团队

---

## 许可证

内部项目，仅供 EBG 商用产品团队使用。 