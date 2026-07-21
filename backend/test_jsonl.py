#!/usr/bin/env python3
"""
测试JSONL内容生成功能
"""

import requests
import json

def test_chunk_with_jsonl():
    """测试分块API并获取JSONL内容"""
    
    # 测试文件路径
    test_file = "test_document.txt"
    
    # 创建测试文件
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("""
第一条 为了规范法律法规的制定和实施，根据宪法，制定本法。

第二条 本法适用于中华人民共和国境内的法律法规制定、修改和废止活动。

第三条 法律法规应当符合宪法，不得与宪法相抵触。

第四条 法律法规的制定应当遵循民主、科学、公开的原则。
        """)
    
    try:
        # 发送请求
        url = "http://localhost:8000/api/chunk/"
        
        with open(test_file, 'rb') as f:
            files = {'file': f}
            data = {'chunker_type': 'law'}
            
            print("🚀 发送分块请求...")
            response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 分块成功!")
            print(f"📊 统计信息: {result['statistics']}")
            print(f"📄 分块数量: {len(result['chunks'])}")
            
            # 显示JSONL内容
            print("\n📋 JSONL格式内容:")
            print("=" * 50)
            print(result['jsonl_content'])
            print("=" * 50)
            
            # 验证JSONL格式
            jsonl_lines = result['jsonl_content'].strip().split('\n')
            print(f"\n🔍 JSONL验证:")
            print(f"   行数: {len(jsonl_lines)}")
            
            for i, line in enumerate(jsonl_lines):
                try:
                    json.loads(line)
                    print(f"   第{i+1}行: ✅ 有效JSON")
                except json.JSONDecodeError as e:
                    print(f"   第{i+1}行: ❌ 无效JSON - {e}")
            
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    finally:
        # 清理测试文件
        import os
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"🧹 清理测试文件: {test_file}")

if __name__ == "__main__":
    test_chunk_with_jsonl()

