import asyncio
import json
import logging
import httpx
from sseclient import SSEClient
import threading
import subprocess
import shutil

logger = logging.getLogger(__name__)

class MCPClient:
    def __init__(self, name):
        self.name = name
        self.tools = []

    async def list_tools(self):
        pass

    async def call_tool(self, tool_name, arguments):
        pass

class SSEMCPClient(MCPClient):
    def __init__(self, name, base_url):
        super().__init__(name)
        self.base_url = base_url.rstrip('/')
        self.sse_url = f"{self.base_url}/mcp/sse"
        self.post_url = f"{self.base_url}/mcp/message" # Assuming standard implementation
        self._listening = False

    async def connect(self):
        # In a real implementation, we'd start a background task to listen to SSE
        # and handshake. For now, we'll assume we can just query tools.
        # But wait, MCP requires initialization.
        logger.info(f"Connecting to SSE MCP Server at {self.sse_url}")
        # Simplified for this task: specific implementation details might vary
        pass

    async def list_tools(self, headers=None):
        # JSON-RPC request to list tools
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.post_url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            if 'result' in result:
                self.tools = result['result'].get('tools', [])
                return self.tools
            return []
    
    async def call_tool(self, tool_name, arguments, headers=None):
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        # Ensure URL is resolved if this is a Nacos client
        if hasattr(self, "_resolve_url"):
            await self._resolve_url()

        async with httpx.AsyncClient() as client:
            response = await client.post(self.post_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json().get('result', {})

class NacosSSEMCPClient(SSEMCPClient):
    def __init__(self, name, target_service_name):
        """
        MCP Client that discovers service address via Nacos.
        :param target_service_name: The service name in Nacos (e.g., 'ai-langchain4j')
        """
        super().__init__(name, "http://uninitialized")
        self.target_service_name = target_service_name

    async def _resolve_url(self):
        """Dynamically resolve service address from Nacos."""
        from app.core.nacos import nacos_manager
        try:
            instances = nacos_manager.get_service(self.target_service_name)
            if not instances:
                logger.error(f"❌ No healthy instances found for {self.target_service_name} in Nacos.")
                return False
            
            # Simple strategy: use the first instance
            instance = instances[0]
            ip = instance.get('ip')
            port = instance.get('port')
            
            self.base_url = f"http://{ip}:{port}"
            self.sse_url = f"{self.base_url}/mcp/sse"
            # 💡 注意：Java 端 McpController 的消息处理路径通常是 /mcp/messages
            self.post_url = f"{self.base_url}/mcp/messages"
            return True
        except Exception as e:
            logger.error(f"❌ Failed to resolve {self.target_service_name} from Nacos: {e}")
            return False

    async def list_tools(self, headers=None):
        if await self._resolve_url():
            return await super().list_tools(headers=headers)
        return []

    async def call_tool(self, tool_name, arguments, headers=None):
        if await self._resolve_url():
            return await super().call_tool(tool_name, arguments, headers=headers)
        return {"error": "Service unavailable"}

class StdioMCPClient(MCPClient):
    def __init__(self, name, command, args):
        super().__init__(name)
        self.command = command
        self.args = args
        self.process = None
        self._response_futures = {}
        self._lock = asyncio.Lock()

    async def connect(self):
        full_command = [self.command] + self.args
        if shutil.which(self.command) is None:
            if self.command == 'npx':
                full_command[0] = 'npx.cmd'
        
        logger.info(f"Starting Stdio MCP Server: {full_command}")
        self.process = await asyncio.create_subprocess_exec(
            *full_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        asyncio.create_task(self._listen_stdout())
        
        # Initialize
        await self._send_json_rpc("initialize", {
            "protocolVersion": "0.1.0",
            "capabilities": {},
            "clientInfo": {"name": "python-agent", "version": "0.1"}
        })
        await self._send_json_rpc("notifications/initialized")

    async def _listen_stdout(self):
        while True:
            line = await self.process.stdout.readline()
            if not line:
                break
            try:
                data = json.loads(line)
                if 'id' in data and data['id'] in self._response_futures:
                    self._response_futures[data['id']].set_result(data)
            except Exception as e:
                logger.error(f"Error parsing JSON from stdio: {e}")

    async def _send_json_rpc(self, method, params=None):
        req_id = 1 # In real app, increment this
        future = asyncio.Future()
        self._response_futures[req_id] = future
        
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {}
        }
        json_str = json.dumps(payload) + "\n"
        self.process.stdin.write(json_str.encode())
        await self.process.stdin.drain()
        
        return await future

    async def list_tools(self):
        response = await self._send_json_rpc("tools/list")
        if response and 'result' in response:
            self.tools = response['result'].get('tools', [])
            return self.tools
        return []

    async def call_tool(self, tool_name, arguments):
        response = await self._send_json_rpc("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        if response and 'result' in response:
            return response['result']
        return {}
# Registry
mcp_clients = {}

def register_mcp_client(client: MCPClient):
    mcp_clients[client.name] = client

async def get_all_tools():
    all_tools = []
    for client in mcp_clients.values():
        try:
            tools = await client.list_tools()
            for t in tools:
                t['client_name'] = client.name # Tag with client name
            all_tools.extend(tools)
        except Exception as e:
            logger.error(f"Error listing tools from {client.name}: {e}")
    return all_tools
