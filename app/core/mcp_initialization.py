import os
import shutil
import sys
import asyncio
from app.services.mcp_client import StdioMCPClient, SSEMCPClient, register_mcp_client
from app.core.nacos import nacos_manager
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


async def setup_mcp_clients():
    # 1. Stdio Client (e.g., Brave Search)
    # We'll use a placeholder command or the one requested if we can find it.
    # The user mentioned "Node.js MCP Server (如 Brave Search)".
    # Let's assume the user has npx and the package.

    # Check config first, then fall back to auto-discovery
    npx_path = settings.MCP_BRAVE_PATH or shutil.which("npx")

    # 2. 安全检查：如果没有安装 Node.js/npx，提前报错
    if not npx_path:
        raise FileNotFoundError(
            "未找到 npx 命令，请确保已安装 Node.js 并添加到环境变量中，或在配置中指定路径。"
        )

    # 3. 初始化本地 Stdio 客户端 (如 Brave Search)
    brave_client = StdioMCPClient(
        name="brave-search",
        command=npx_path,
        args=["-y", "@modelcontextprotocol/server-brave-search"],
    )
    register_mcp_client(brave_client)

    # 4. 🔥 注册支持 Nacos 动态发现的 Java SSE 客户端
    from app.services.mcp_client import NacosSSEMCPClient
    java_client = NacosSSEMCPClient(
        name="java-service",
        target_service_name=settings.NACOS_JAVA_SERVICE_NAME
    )
    register_mcp_client(java_client)
    logger.info(f"✅ Registered Nacos-based MCP client for service: {settings.NACOS_JAVA_SERVICE_NAME}")


async def connect_clients():
    """后台任务：启动已注册客户端的连接或预解析逻辑。"""
    from app.services.mcp_client import mcp_clients

    # 1. 连接本地 Stdio 客户端
    try:
        if "brave-search" in mcp_clients:
            await mcp_clients["brave-search"].connect()
            logger.info("🚀 Brave Search MCP client connected.")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Brave Search: {e}")

    # 2. 预解析 Java 服务地址 (确保发现逻辑正常)
    try:
        client = mcp_clients.get("java-service")
        if client and hasattr(client, "_resolve_url"):
            success = await client._resolve_url()
            if success:
                logger.info(f"🚀 Java service resolved at {client.base_url}")
            else:
                logger.warning(f"⚠️ Java service ({settings.NACOS_JAVA_SERVICE_NAME}) not found in Nacos yet.")
    except Exception as e:
        logger.error(f"❌ Error during Java service discovery: {e}")
