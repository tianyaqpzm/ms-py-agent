import os
import sys
import glob
import httpx
import asyncio

# The endpoint of your running ms-py-agent service
INGEST_URL = "http://localhost:8181/rest/kb/v1/documents/ingest"

async def ingest_file(client: httpx.AsyncClient, file_path: str):
    abs_path = os.path.abspath(file_path)
    # Get the file name as a potential dish name
    filename = os.path.basename(abs_path)
    
    # Optional: Skip files that aren't recipes
    if filename.lower() in ["readme.md", "contributing.md", "template.md"]:
        return

    payload = {
        "file_path": abs_path,
        "category": "HowToCook",  # This will be used in Retrieval filtering
        "tenant_id": "default"
    }

    try:
        response = await client.post(INGEST_URL, json=payload, timeout=120.0)
        if response.status_code == 201:
            data = response.json()
            print(f"✅ 成功入库: {filename} - {data['metrics']['chunks_inserted']} 个分块")
        else:
            print(f"❌ 入库失败: {filename} - 状态码: {response.status_code} - 详情: {response.text}")
    except Exception as e:
        print(f"⚠️ 请求异常: {filename} - {e}")

async def main(repo_path: str):
    if not os.path.exists(repo_path):
        print(f"找不到路径: {repo_path}")
        sys.exit(1)

    print(f"开始扫描目录 {repo_path} 下的 Markdown 文件...\n")
    # Search for all markdown files recursively
    md_files = glob.glob(os.path.join(repo_path, "**/*.md"), recursive=True)
    
    print(f"找到 {len(md_files)} 个 Markdown 文件，准备开始导入。")
    print("-" * 50)

    # Use a single async client for all requests
    async with httpx.AsyncClient() as client:
        # To avoid overwhelming your local DB/Embedding model, 
        # we can do it entirely sequentially or with a semaphore. 
        # Here we do it sequentially for safety.
        for file in md_files:
            await ingest_file(client, file)

    print("\n🎉 全部食谱入库任务已完成！")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/ingest_how_to_cook.py <HowToCook_仓库绝对路径>")
        sys.exit(1)
    
    target_repo = sys.argv[1]
    asyncio.run(main(target_repo))
