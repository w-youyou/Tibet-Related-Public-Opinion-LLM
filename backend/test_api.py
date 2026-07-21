#!/usr/bin/env python3
"""
API测试脚本
用于测试分块器API接口
"""

import requests
import json
import os

# API基础URL
BASE_URL = "http://localhost:8000/api"

def test_health_check():
    """测试健康检查接口"""
    print("测试健康检查接口...")
    try:
        response = requests.get(f"{BASE_URL}/health/")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"健康检查失败: {e}")
        return False

def test_get_chunkers():
    """测试获取分块器信息接口"""
    print("\n测试获取分块器信息接口...")
    try:
        response = requests.get(f"{BASE_URL}/chunkers/")
        print(f"状态码: {response.status_code}")
        data = response.json()
        print(f"分块器数量: {len(data.get('chunkers', {}))}")
        for chunker_type, info in data.get('chunkers', {}).items():
            print(f"  {chunker_type}: {info['name']}")
        return response.status_code == 200
    except Exception as e:
        print(f"获取分块器信息失败: {e}")
        return False

def test_chunk_document():
    """测试文档分块接口"""
    print("\n测试文档分块接口...")
    
    # 创建一个测试文件
    test_content = """
    问：什么是人工智能？
    答：人工智能（AI）是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。

    问：机器学习是什么？
    答：机器学习是人工智能的一个子领域，通过算法让计算机从数据中学习模式。

    问：深度学习有什么特点？
    答：深度学习使用多层神经网络来模拟人脑的学习过程，在图像识别、自然语言处理等领域取得了突破性进展。
    """
    
    # 创建临时测试文件
    test_file_path = "test_qa.txt"
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(test_content)
    
    try:
        # 测试文件上传和分块
        with open(test_file_path, "rb") as f:
            files = {"file": f}
            data = {"chunker_type": "qa"}
            
            response = requests.post(f"{BASE_URL}/chunk/", files=files, data=data)
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"成功处理文档: {result['file_name']}")
                print(f"分块器类型: {result['chunker_type']}")
                print(f"分块数量: {len(result['chunks'])}")
                print(f"统计信息: {result['statistics']}")
                
                # 显示前几个分块
                for i, chunk in enumerate(result['chunks'][:2]):
                    print(f"\n分块 {i+1}:")
                    print(f"  ID: {chunk['id']}")
                    print(f"  内容: {chunk['content'][:100]}...")
                    print(f"  元数据: {chunk['metadata']}")
            else:
                print(f"分块失败: {response.text}")
            
            return response.status_code == 200
            
    except Exception as e:
        print(f"文档分块测试失败: {e}")
        return False
    finally:
        # 清理测试文件
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

def main():
    """主测试函数"""
    print("开始API测试...")
    
    tests = [
        ("健康检查", test_health_check),
        ("获取分块器信息", test_get_chunkers),
        ("文档分块", test_chunk_document),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"测试: {test_name}")
        print('='*50)
        
        success = test_func()
        results.append((test_name, success))
        
        if success:
            print(f"✅ {test_name} 测试通过")
        else:
            print(f"❌ {test_name} 测试失败")
    
    # 输出测试总结
    print(f"\n{'='*50}")
    print("测试总结")
    print('='*50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！API服务运行正常。")
    else:
        print("⚠️  部分测试失败，请检查API服务状态。")

if __name__ == "__main__":
    main()
