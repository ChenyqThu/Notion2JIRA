#!/usr/bin/env node

/**
 * 测试脚本：验证多Redis DB路由功能
 * 
 * 用途：
 * 1. 测试不同database_id的webhook请求是否路由到正确的Redis DB
 * 2. 验证健康检查和管理接口功能
 * 3. 模拟真实的Notion webhook请求
 */

const axios = require('axios');
const Redis = require('redis');

// 配置
const WEBHOOK_SERVER_URL = 'http://localhost:7654';
const REDIS_CONFIG = {
  host: process.env.REDIS_HOST || 'localhost',
  port: process.env.REDIS_PORT || 6379,
  password: process.env.REDIS_PASSWORD || undefined
};

// 测试数据
const TEST_DATABASES = {
  network: {
    id: '19a15375830d81cbb107f8131b2d4cc0',
    expectedRedisDB: 0,
    name: '网络需求池'
  },
  security: {
    id: '1af15375830d804e9d13c24f3d0a3424', 
    expectedRedisDB: 1,
    name: '安防需求池'
  }
};

class RoutingTester {
  constructor() {
    this.redisClients = new Map();
    this.testResults = [];
  }

  async initialize() {
    console.log('🚀 初始化路由测试器...');
    
    // 创建Redis客户端连接到不同数据库
    for (const [name, config] of Object.entries(TEST_DATABASES)) {
      const client = Redis.createClient({
        ...REDIS_CONFIG,
        database: config.expectedRedisDB
      });
      
      await client.connect();
      this.redisClients.set(config.expectedRedisDB, { client, name });
      console.log(`✅ Redis DB ${config.expectedRedisDB} (${config.name}) 连接成功`);
    }
  }

  async cleanup() {
    console.log('🧹 清理资源...');
    for (const [_, { client }] of this.redisClients) {
      if (client) {
        await client.quit();
      }
    }
  }

  async testHealthCheck() {
    console.log('\n📊 测试健康检查端点...');
    
    try {
      const response = await axios.get(`${WEBHOOK_SERVER_URL}/health`);
      console.log('✅ 健康检查响应:', JSON.stringify(response.data, null, 2));
      
      // 验证Redis状态
      const redisStatus = response.data.redis;
      if (redisStatus.initialized && Object.keys(redisStatus.databases).length >= 2) {
        console.log('✅ 多Redis数据库状态正常');
        return true;
      } else {
        console.log('❌ Redis状态异常');
        return false;
      }
    } catch (error) {
      console.log('❌ 健康检查失败:', error.message);
      return false;
    }
  }

  async testAdminStatus() {
    console.log('\n📈 测试管理状态端点...');
    
    try {
      const response = await axios.get(`${WEBHOOK_SERVER_URL}/admin/status`, {
        headers: {
          'X-API-Key': process.env.ADMIN_API_KEY || 'test-key'
        }
      });
      
      console.log('✅ 管理状态响应:', JSON.stringify(response.data.data.redis, null, 2));
      console.log('✅ 队列状态:', JSON.stringify(response.data.data.queues, null, 2));
      return true;
    } catch (error) {
      console.log('❌ 管理状态查询失败:', error.response?.data || error.message);
      return false;
    }
  }

  async clearAllQueues() {
    console.log('\n🧹 清空所有队列...');
    
    for (const [dbNumber, { client, name }] of this.redisClients) {
      try {
        await client.del('sync_queue');
        console.log(`✅ 清空 Redis DB ${dbNumber} (${name}) 的队列`);
      } catch (error) {
        console.log(`❌ 清空 Redis DB ${dbNumber} 队列失败:`, error.message);
      }
    }
  }

  async createTestWebhookPayload(databaseId) {
    return {
      source: {
        type: 'automation'
      },
      data: {
        id: `test-page-${Date.now()}`,
        object: 'page',
        parent: {
          database_id: databaseId
        },
        last_edited_time: new Date().toISOString(),
        created_time: new Date().toISOString(),
        archived: false,
        in_trash: false,
        properties: {
          '功能 Name': {
            type: 'title',
            title: [
              {
                plain_text: `测试页面 - ${Date.now()}`,
                text: { content: `测试页面 - ${Date.now()}` }
              }
            ]
          },
          'sync2jira': {
            type: 'checkbox',
            checkbox: true
          },
          '优先级 Priority': {
            type: 'select',
            select: {
              name: '高 High'
            }
          }
        }
      }
    };
  }

  async sendTestWebhook(databaseConfig) {
    console.log(`\n📮 发送测试webhook到 ${databaseConfig.name}...`);
    
    const payload = await this.createTestWebhookPayload(databaseConfig.id);
    
    try {
      const response = await axios.post(`${WEBHOOK_SERVER_URL}/webhook/notion`, payload, {
        headers: {
          'Content-Type': 'application/json',
          'Notion-Webhook-Signature': 'test-signature',
          'Notion-Webhook-Timestamp': Math.floor(Date.now() / 1000).toString()
        }
      });
      
      console.log(`✅ Webhook请求成功: ${response.data.message}`);
      return {
        success: true,
        pageId: payload.data.id,
        databaseId: databaseConfig.id,
        expectedRedisDB: databaseConfig.expectedRedisDB
      };
    } catch (error) {
      console.log(`❌ Webhook请求失败:`, error.response?.data || error.message);
      return {
        success: false,
        error: error.message,
        databaseId: databaseConfig.id
      };
    }
  }

  async verifyRouting(testResult) {
    console.log(`\n🔍 验证路由结果 (预期Redis DB: ${testResult.expectedRedisDB})...`);
    
    // 等待一下让消息处理完成
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    try {
      const expectedClient = this.redisClients.get(testResult.expectedRedisDB)?.client;
      if (!expectedClient) {
        console.log(`❌ 找不到Redis DB ${testResult.expectedRedisDB}的客户端`);
        return false;
      }
      
      // 检查预期数据库中是否有消息
      const queueLength = await expectedClient.lLen('sync_queue');
      console.log(`📊 Redis DB ${testResult.expectedRedisDB} 队列长度: ${queueLength}`);
      
      if (queueLength > 0) {
        // 检查消息内容
        const message = await expectedClient.lRange('sync_queue', -1, -1);
        const parsedMessage = JSON.parse(message[0]);
        
        if (parsedMessage.data.event_data.database_id === testResult.databaseId) {
          console.log(`✅ 路由验证成功! 消息已正确路由到Redis DB ${testResult.expectedRedisDB}`);
          console.log(`📝 消息详情:`, {
            database_id: parsedMessage.data.event_data.database_id,
            page_id: parsedMessage.data.event_data.page_id,
            redis_db: parsedMessage.database_id || 'unknown'
          });
          return true;
        } else {
          console.log(`❌ 数据库ID不匹配! 预期: ${testResult.databaseId}, 实际: ${parsedMessage.data.event_data.database_id}`);
          return false;
        }
      } else {
        console.log(`❌ 预期的Redis DB ${testResult.expectedRedisDB} 中没有找到消息`);
        
        // 检查其他数据库是否误接收了消息
        for (const [dbNumber, { client, name }] of this.redisClients) {
          if (dbNumber !== testResult.expectedRedisDB) {
            const wrongQueueLength = await client.lLen('sync_queue');
            if (wrongQueueLength > 0) {
              console.log(`⚠️  消息可能被误路由到Redis DB ${dbNumber} (${name}), 队列长度: ${wrongQueueLength}`);
            }
          }
        }
        return false;
      }
    } catch (error) {
      console.log(`❌ 验证路由失败:`, error.message);
      return false;
    }
  }

  async runFullTest() {
    console.log('🧪 开始完整路由测试...');
    
    try {
      // 初始化
      await this.initialize();
      
      // 清空队列
      await this.clearAllQueues();
      
      // 测试健康检查
      const healthOK = await this.testHealthCheck();
      if (!healthOK) {
        throw new Error('健康检查失败');
      }
      
      // 测试管理接口
      await this.testAdminStatus();
      
      // 测试每个数据库的路由
      for (const [name, databaseConfig] of Object.entries(TEST_DATABASES)) {
        console.log(`\n🎯 测试 ${name} 数据库路由...`);
        
        // 发送webhook
        const webhookResult = await this.sendTestWebhook(databaseConfig);
        if (!webhookResult.success) {
          continue;
        }
        
        // 验证路由
        const routingOK = await this.verifyRouting(webhookResult);
        this.testResults.push({
          database: name,
          webhook: webhookResult.success,
          routing: routingOK
        });
      }
      
      // 输出测试结果
      this.printTestResults();
      
    } catch (error) {
      console.error('❌ 测试失败:', error.message);
    } finally {
      await this.cleanup();
    }
  }

  printTestResults() {
    console.log('\n📋 测试结果汇总:');
    console.log('==================');
    
    let allPassed = true;
    for (const result of this.testResults) {
      const status = result.webhook && result.routing ? '✅ 通过' : '❌ 失败';
      console.log(`${result.database}: ${status}`);
      if (!result.webhook || !result.routing) {
        allPassed = false;
      }
    }
    
    console.log('==================');
    console.log(allPassed ? '🎉 所有测试通过!' : '💥 部分测试失败!');
  }
}

// 运行测试
if (require.main === module) {
  const tester = new RoutingTester();
  tester.runFullTest().then(() => {
    process.exit(0);
  }).catch(error => {
    console.error('测试运行失败:', error);
    process.exit(1);
  });
}

module.exports = RoutingTester;