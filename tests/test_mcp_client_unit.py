"""
MCP Client 单元测试：JSON-RPC 构造、服务发现、工具聚合
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.mcp_client import (
    MCPClient, SSEMCPClient, NacosSSEMCPClient,
    mcp_clients, register_mcp_client, get_all_tools
)


class TestSSEMCPClient:
    """PC-01 ~ PC-02: SSE MCP Client JSON-RPC 消息构造"""

    # PC-01: list_tools 构造正确的 JSON-RPC
    @pytest.mark.asyncio
    async def test_list_tools_constructs_correct_jsonrpc(self):
        client = SSEMCPClient("test-java", "http://localhost:8080")

        # Mock httpx 请求
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "tools": [{"name": "query_order", "description": "查询订单"}]
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            tools = await client.list_tools()

            # 验证 POST 调用参数
            call_args = mock_client_instance.post.call_args
            payload = call_args.kwargs.get("json") or call_args[1].get("json")
            assert payload["method"] == "tools/list"
            assert payload["jsonrpc"] == "2.0"
            assert len(tools) == 1

    # PC-02: call_tool 构造正确的 JSON-RPC
    @pytest.mark.asyncio
    async def test_call_tool_constructs_correct_jsonrpc(self):
        client = SSEMCPClient("test-java", "http://localhost:8080")

        mock_response = MagicMock()
        mock_response.json.return_value = {"result": {"content": [{"type": "text", "text": "OK"}]}}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            result = await client.call_tool("query_order", {"orderId": "123"})

            call_args = mock_client_instance.post.call_args
            payload = call_args.kwargs.get("json") or call_args[1].get("json")
            assert payload["method"] == "tools/call"
            assert payload["params"]["name"] == "query_order"
            assert payload["params"]["arguments"] == {"orderId": "123"}


class TestNacosSSEMCPClient:
    """PC-03: 服务地址解析"""

    # PC-03: _resolve_url 正确拼接
    @pytest.mark.asyncio
    async def test_resolve_url_builds_correct_base_url(self):
        client = NacosSSEMCPClient("java-mcp", "ai-langchain4j")

        with patch("app.core.nacos.nacos_manager") as mock_nacos:
            mock_nacos.get_service.return_value = [
                {"ip": "192.168.1.100", "port": 8080}
            ]

            result = await client._resolve_url()

            assert result is True
            assert client.base_url == "http://192.168.1.100:8080"
            assert client.post_url == "http://192.168.1.100:8080/mcp/messages"


class TestGetAllTools:
    """PC-04: 工具聚合"""

    # PC-04: 聚合多个客户端工具并打上 client_name 标签
    @pytest.mark.asyncio
    async def test_get_all_tools_aggregates_and_tags(self):
        # 清空并注册测试客户端
        mcp_clients.clear()

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.name = "test-client"
        mock_client.list_tools = AsyncMock(return_value=[
            {"name": "tool_a", "description": "Tool A"},
            {"name": "tool_b", "description": "Tool B"},
        ])
        mcp_clients["test-client"] = mock_client

        tools = await get_all_tools()

        assert len(tools) == 2
        assert all(t.get("client_name") == "test-client" for t in tools)

        # 清理
        mcp_clients.clear()
