# Webhook Server 变更日志

## [v1.1.0] - 2024-01-15

### 🚀 新增功能

#### 增强的字段存储策略
- **双重存储结构**：同时保存解析后的数据和原始数据
  - `properties`: 解析后的易用格式
  - `raw_properties`: 完整的原始 Notion 数据
- **扩展字段类型支持**：
  - 新增：`email`, `phone_number`, `number`, `date`, `files`
  - 新增：`created_by`, `last_edited_by`, `unique_id`, `verification`
  - 改进：`people`, `relation`, `rollup` 字段的解析
- **未知字段类型处理**：自动保存新字段类型的原始数据，便于未来扩展
- **容错机制**：解析失败时保存原始数据和错误信息

#### CORS 配置优化
- **CORS 开关**：新增 `CORS_ENABLED` 环境变量
- **开发环境友好**：开发环境自动允许所有来源，方便本地调试
- **灵活配置**：生产环境可严格控制允许的来源

#### 端口配置标准化
- **默认端口**：统一使用 7654 作为默认端口
- **配置一致性**：server.js、ecosystem.config.js、env.example 保持一致

### 🔧 重大变更

#### 移除 Formula 字段依赖
- **同步触发逻辑**：不再依赖 Formula 字段判断是否同步
- **新的同步控制**：
  - 主要通过 Button Property 点击触发
  - 支持 checkbox 字段控制：`sync2jira`、`同步到JIRA`、`Sync to JIRA`
  - 默认策略：收到 webhook 即认为需要同步

#### 属性解析结构变更
- **旧格式**：`properties[fieldName] = value`
- **新格式**：
  ```json
  {
    "properties": {
      "fieldName": {
        "type": "字段类型",
        "value": "解析后的值",
        "raw": "原始数据"
      }
    },
    "raw_properties": {
      "fieldName": "完整原始数据"
    }
  }
  ```

### 🗑️ 移除功能

#### 部署脚本移除
- **移除文件**：`deploy.sh` 一键部署脚本
- **替代方案**：提供详细的手动部署文档
- **新增部署方式**：
  - 手动部署步骤（推荐）
  - Docker Compose 部署
  - 本地开发部署

### 📚 文档更新

#### README.md 全面更新
- **部署指南**：详细的手动部署步骤
- **字段存储策略**：新的字段解析和存储机制说明
- **CORS 配置**：新增 CORS 开关的使用说明
- **端口配置**：更新所有端口引用为 7654
- **示例更新**：移除 Formula 字段相关示例

#### 新增测试脚本
- **字段解析测试**：`scripts/test-field-parsing.js`
- **功能验证**：验证新的字段存储策略
- **调试支持**：支持 `--verbose` 参数查看详细结果

### 🔄 兼容性说明

#### 向后兼容
- **API 接口**：保持现有 API 接口不变
- **环境变量**：新增变量有默认值，不影响现有部署
- **数据格式**：新格式包含更多信息，但保持核心数据可访问

#### 迁移建议
1. **更新环境变量**：添加 `CORS_ENABLED=true` 到 `.env` 文件
2. **检查端口配置**：确认使用端口 7654
3. **更新同步逻辑**：如果有自定义同步控制，请适配新的字段格式
4. **测试字段解析**：运行 `node scripts/test-field-parsing.js` 验证

### 🐛 修复问题

- **字段解析错误**：改进错误处理，避免单个字段解析失败影响整体处理
- **标题提取逻辑**：支持多种标题字段名称，提高兼容性
- **日志记录**：优化日志信息，增加字段数量统计

### 🔮 未来计划

- **字段映射配置**：支持自定义字段映射规则
- **批量处理**：支持批量 webhook 事件处理
- **性能优化**：优化大量字段的解析性能
- **监控增强**：增加更多监控指标和告警

---

## 升级指南

### 从 v1.0.0 升级到 v1.1.0

1. **备份现有配置**
   ```bash
   cp .env .env.backup
   ```

2. **更新代码**
   ```bash
   git pull origin main
   npm install
   ```

3. **更新环境变量**
   ```bash
   # 添加到 .env 文件
   CORS_ENABLED=true
   ```

4. **验证配置**
   ```bash
   node scripts/test-field-parsing.js
   ```

5. **重启服务**
   ```bash
   pm2 restart notion-webhook
   ```

### 注意事项

- 如果你的同步服务依赖特定的字段格式，请检查并更新相关代码
- 新的字段格式提供了更多信息，建议利用 `raw` 数据获取完整的 Notion 字段信息
- 如果遇到问题，可以临时设置 `CORS_ENABLED=false` 禁用 CORS 检查 