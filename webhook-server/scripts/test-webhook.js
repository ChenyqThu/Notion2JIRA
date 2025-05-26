#!/usr/bin/env node

/**
 * Notion Webhook 测试脚本
 * 用于测试 webhook 服务器是否正常工作
 */

const axios = require('axios');

// 配置
const WEBHOOK_URL = process.env.WEBHOOK_URL || 'http://localhost:7654';
const ADMIN_API_KEY = process.env.ADMIN_API_KEY || 'test-admin-key';

/**
 * 测试健康检查
 */
async function testHealthCheck() {
  console.log('🔍 测试健康检查...');
  try {
    const response = await axios.get(`${WEBHOOK_URL}/health`);
    console.log('✅ 健康检查通过:', response.data.status);
    return true;
  } catch (error) {
    console.error('❌ 健康检查失败:', error.message);
    return false;
  }
}

/**
 * 测试 Webhook 接收
 */
async function testWebhookReceive() {
  console.log('🔍 测试 Webhook 接收...');
  
  const testEvent = {
    event_type: 'page.updated',
    page_id: 'test-page-' + Date.now(),
    database_id: 'test-database-id',
    properties: {
      title: 'Test Page from Script',
      sync2jira: true,
      priority: 'Medium'
    }
  };

  try {
    const response = await axios.post(`${WEBHOOK_URL}/webhook/notion`, testEvent, {
      headers: {
        'Content-Type': 'application/json'
      }
    });

    console.log('✅ Webhook 接收成功:', response.data.result);
    return true;
  } catch (error) {
    console.error('❌ Webhook 接收失败:', error.response?.data || error.message);
    return false;
  }
}

/**
 * 测试管理接口
 */
async function testAdminAPI() {
  console.log('🔍 测试管理接口...');
  
  try {
    const response = await axios.get(`${WEBHOOK_URL}/admin/status`, {
      headers: {
        'X-API-Key': ADMIN_API_KEY
      }
    });

    console.log('✅ 管理接口访问成功:', {
      service: response.data.data.service,
      version: response.data.data.version,
      redis_connected: response.data.data.redis.connected
    });
    return true;
  } catch (error) {
    console.error('❌ 管理接口访问失败:', error.response?.data || error.message);
    return false;
  }
}

/**
 * 测试队列功能
 */
async function testQueueStats() {
  console.log('🔍 测试队列统计...');
  
  try {
    const response = await axios.get(`${WEBHOOK_URL}/admin/queue/stats`, {
      headers: {
        'X-API-Key': ADMIN_API_KEY
      }
    });

    console.log('✅ 队列统计获取成功:', response.data.data.queues);
    return true;
  } catch (error) {
    console.error('❌ 队列统计获取失败:', error.response?.data || error.message);
    return false;
  }
}

/**
 * 主测试函数
 */
async function runTests() {
  console.log('🚀 开始测试 Notion Webhook 服务器');
  console.log('📍 服务器地址:', WEBHOOK_URL);
  console.log('');

  const tests = [
    { name: '健康检查', fn: testHealthCheck },
    { name: 'Webhook 接收', fn: testWebhookReceive },
    { name: '管理接口', fn: testAdminAPI },
    { name: '队列统计', fn: testQueueStats }
  ];

  let passed = 0;
  let failed = 0;

  for (const test of tests) {
    console.log(`\n--- ${test.name} ---`);
    try {
      const result = await test.fn();
      if (result) {
        passed++;
        console.log(`✅ ${test.name} 测试通过`);
      } else {
        failed++;
        console.log(`❌ ${test.name} 测试失败`);
      }
    } catch (error) {
      failed++;
      console.error(`❌ ${test.name} 测试异常:`, error.message);
    }
  }

  console.log('\n' + '='.repeat(50));
  console.log(`📊 测试结果: ${passed} 通过, ${failed} 失败`);
  
  if (failed === 0) {
    console.log('🎉 所有测试都通过了！');
    process.exit(0);
  } else {
    console.log('💥 有测试失败，请检查服务器配置');
    process.exit(1);
  }
}

// 运行测试
if (require.main === module) {
  runTests().catch(error => {
    console.error('测试运行失败:', error);
    process.exit(1);
  });
} 