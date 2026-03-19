#!/usr/bin/env python3
"""
测试API速率限制功能
"""

import requests
import time
import json

BASE_URL = "http://localhost:5000/api"

def test_rate_limit_info():
    """测试速率限制信息端点"""
    print("测试1: 速率限制信息端点")
    
    response = requests.get(f"{BASE_URL}/rate-limit/info")
    print(f"  状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"  成功: {data.get('success')}")
        print(f"  限制配置数量: {len(data.get('limits', []))}")
        
        # 打印限制配置
        for limit in data.get('limits', []):
            print(f"    - {limit['name']}: {limit['limit']}")
        
        # 打印客户端信息
        client_info = data.get('client_info', {})
        print(f"  客户端IP: {client_info.get('ip')}")
        print(f"  用户标识: {client_info.get('user')}")
    
    return response.status_code == 200

def test_auth_rate_limit():
    """测试认证接口速率限制"""
    print("\n测试2: 认证接口速率限制")
    
    # 测试注册接口（应该被限制）
    test_data = {
        "username": "testuser_" + str(int(time.time())),
        "password": "testpassword123"
    }
    
    print(f"  测试用户: {test_data['username']}")
    
    # 快速连续请求（应该触发限制）
    responses = []
    for i in range(15):  # 超过10次/分钟的限制
        response = requests.post(f"{BASE_URL}/auth/register", json=test_data)
        responses.append({
            "attempt": i + 1,
            "status": response.status_code,
            "headers": dict(response.headers)
        })
        time.sleep(0.1)  # 稍微延迟
    
    # 分析结果
    success_count = sum(1 for r in responses if r["status"] == 200)
    rate_limit_count = sum(1 for r in responses if r["status"] == 429)
    
    print(f"  总请求数: {len(responses)}")
    print(f"  成功请求: {success_count}")
    print(f"  被限制请求: {rate_limit_count}")
    
    # 检查是否有限制头部
    limited_responses = [r for r in responses if r["status"] == 429]
    if limited_responses:
        print(f"  第一个被限制的响应:")
        print(f"    状态码: {limited_responses[0]['status']}")
        print(f"    头部: X-RateLimit-Limit: {limited_responses[0]['headers'].get('X-RateLimit-Limit', 'N/A')}")
        print(f"    头部: X-RateLimit-Remaining: {limited_responses[0]['headers'].get('X-RateLimit-Remaining', 'N/A')}")
    
    return rate_limit_count > 0

def test_funds_rate_limit():
    """测试基金数据接口速率限制"""
    print("\n测试3: 基金数据接口速率限制")
    
    responses = []
    for i in range(35):  # 超过30次/分钟的限制
        response = requests.get(f"{BASE_URL}/funds")
        responses.append({
            "attempt": i + 1,
            "status": response.status_code,
            "headers": dict(response.headers)
        })
        time.sleep(0.05)  # 更快的请求
    
    # 分析结果
    success_count = sum(1 for r in responses if r["status"] == 200)
    rate_limit_count = sum(1 for r in responses if r["status"] == 429)
    
    print(f"  总请求数: {len(responses)}")
    print(f"  成功请求: {success_count}")
    print(f"  被限制请求: {rate_limit_count}")
    
    # 检查速率限制头部
    if success_count > 0:
        first_success = [r for r in responses if r["status"] == 200][0]
        print(f"  成功响应头部:")
        print(f"    X-RateLimit-Limit: {first_success['headers'].get('X-RateLimit-Limit', 'N/A')}")
        print(f"    X-RateLimit-Remaining: {first_success['headers'].get('X-RateLimit-Remaining', 'N/A')}")
        print(f"    X-RateLimit-Reset: {first_success['headers'].get('X-RateLimit-Reset', 'N/A')}")
    
    return rate_limit_count > 0

def test_different_endpoints():
    """测试不同端点的独立限制"""
    print("\n测试4: 不同端点的独立限制")
    
    endpoints = [
        ("/funds", "基金列表"),
        ("/quant/timing-signals", "择时信号"),
        ("/holdings", "持仓列表"),
    ]
    
    results = {}
    for endpoint, name in endpoints:
        print(f"  测试端点: {name} ({endpoint})")
        
        responses = []
        for i in range(25):  # 25次请求
            response = requests.get(f"{BASE_URL}{endpoint}")
            responses.append({
                "attempt": i + 1,
                "status": response.status_code
            })
            time.sleep(0.03)
        
        success = sum(1 for r in responses if r["status"] == 200)
        limited = sum(1 for r in responses if r["status"] == 429)
        
        results[endpoint] = {
            "name": name,
            "total": len(responses),
            "success": success,
            "limited": limited,
            "limited_percentage": limited / len(responses) * 100 if len(responses) > 0 else 0
        }
        
        print(f"    结果: {success}成功, {limited}被限制 ({results[endpoint]['limited_percentage']:.1f}%)")
    
    return results

def test_rate_limit_reset():
    """测试速率限制重置"""
    print("\n测试5: 速率限制重置测试")
    
    # 先触发限制
    print("  步骤1: 触发限制")
    responses = []
    for i in range(40):  # 肯定触发限制
        response = requests.get(f"{BASE_URL}/funds")
        responses.append(response.status_code)
        time.sleep(0.02)
    
    limited_count = responses.count(429)
    print(f"    触发限制: {limited_count}/{len(responses)} 请求被限制")
    
    # 等待一段时间（模拟用户等待）
    print("  步骤2: 等待5秒后重试")
    time.sleep(5)
    
    # 再次尝试
    retry_responses = []
    for i in range(5):
        response = requests.get(f"{BASE_URL}/funds")
        retry_responses.append(response.status_code)
        time.sleep(0.5)
    
    retry_success = retry_responses.count(200)
    print(f"    重试结果: {retry_success}/{len(retry_responses)} 成功")
    
    return retry_success > 0

def test_error_handling():
    """测试错误处理"""
    print("\n测试6: 速率限制错误处理")
    
    # 触发限制并检查错误响应格式
    responses = []
    for i in range(40):
        response = requests.get(f"{BASE_URL}/funds")
        responses.append(response)
        time.sleep(0.02)
    
    # 找到第一个被限制的响应
    limited_response = None
    for resp in responses:
        if resp.status_code == 429:
            limited_response = resp
            break
    
    if limited_response:
        print(f"  限制响应状态码: {limited_response.status_code}")
        
        try:
            error_data = limited_response.json()
            print(f"  错误响应格式:")
            print(f"    成功: {error_data.get('success')}")
            print(f"    错误码: {error_data.get('error', {}).get('code')}")
            print(f"    错误名: {error_data.get('error', {}).get('name')}")
            print(f"    消息: {error_data.get('error', {}).get('message')}")
            
            details = error_data.get('error', {}).get('details', {})
            print(f"    详情:")
            for key, value in details.items():
                print(f"      {key}: {value}")
            
            return True
        except Exception as e:
            print(f"  解析错误响应失败: {e}")
            return False
    else:
        print("  未触发限制")
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("Fund Daily API 速率限制功能测试")
    print("=" * 60)
    
    try:
        # 先检查服务是否正常
        health_response = requests.get(f"{BASE_URL}/health")
        if health_response.status_code != 200:
            print("❌ 服务不可用")
            return
        
        print("✅ 服务正常")
        
        # 运行测试
        tests = [
            ("速率限制信息", test_rate_limit_info),
            ("认证接口限制", test_auth_rate_limit),
            ("基金接口限制", test_funds_rate_limit),
            ("不同端点独立限制", test_different_endpoints),
            ("限制重置测试", test_rate_limit_reset),
            ("错误处理测试", test_error_handling),
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n▶️ 运行测试: {test_name}")
            try:
                result = test_func()
                results.append((test_name, result))
                print(f"  结果: {'✅ 通过' if result else '❌ 失败'}")
            except Exception as e:
                print(f"  测试异常: {e}")
                results.append((test_name, False))
        
        # 总结
        print("\n" + "=" * 60)
        print("测试总结:")
        print("=" * 60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        print(f"通过测试: {passed}/{total} ({passed/total*100:.1f}%)")
        
        for test_name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"  {test_name}: {status}")
        
        print("\n" + "=" * 60)
        if passed == total:
            print("🎉 所有速率限制测试通过！")
            print("速率限制功能已成功集成到API端点。")
        else:
            print("⚠️  部分测试失败，需要检查实现。")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()