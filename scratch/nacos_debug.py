import nacos
import logging
import os
import sys

# 配置日志查看详细 HTTP 过程
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nacos_test")

def test_nacos():
    # 模拟从环境变量读取 (请确保你运行前设置了这些变量，或者直接在这里硬编码)
    server_addr = os.getenv("NACOS_SERVER_ADDR", "tao-lan.122577.xyz:18848")
    username = os.getenv("NACOS_USERNAME", "nacos")
    password = os.getenv("NACOS_PASSWORD", "Qq062525")
    
    # 我们测试两种常见的 Namespace 情况
    namespaces_to_try = [
        ("", "Default/Public (Empty ID)"),
        ("public", "Explicit 'public' string"),
    ]

    print("="*50)
    print(f"🚀 Starting Nacos Connection Test")
    print(f"📍 Server: {server_addr}")
    print(f"👤 User: {username}")
    print(f"🔑 Password: {'Set' if password else 'Not Set'}")
    print("="*50)

    for ns_id, ns_name in namespaces_to_try:
        print(f"\n[Testing Namespace: {ns_name} (ID: '{ns_id}')]")
        try:
            client = nacos.NacosClient(server_addr, namespace=ns_id, username=username, password=password)
            
            # 尝试获取一个配置来验证权限 (DataID 随意填一个可能存在的)
            print("  - Attempting to fetch config...")
            # 注意：如果 DataID 不存在通常返回 None 而不会报错。如果是 403 则是权限问题。
            config = client.get_config("python-agent-development.yaml", "DEFAULT_GROUP")
            
            if config:
                print(f"  ✅ SUCCESS! Received config (first 50 chars): {config[:50]}...")
            else:
                print("  ⚠️ Connected, but config returned None (might just be a wrong DataID/Group).")
                
            # 尝试列出实例 (验证 Naming 权限)
            print("  - Attempting to list naming instances...")
            instances = client.list_naming_instance("python-agent")
            print(f"  ✅ SUCCESS! Found {len(instances)} instances.")

        except Exception as e:
            print(f"  ❌ FAILED: {type(e).__name__}: {e}")
            if "403" in str(e):
                print("  💡 HINT: 403 Forbidden usually means Wrong Password OR User has no permission for this Namespace ID.")

if __name__ == "__main__":
    if not os.getenv("NACOS_PASSWORD"):
        print("❌ ERROR: Please set NACOS_PASSWORD environment variable before running.")
        # sys.exit(1)
    test_nacos()
