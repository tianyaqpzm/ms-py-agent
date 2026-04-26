"""
LangGraph 图结构测试：路由逻辑、图节点验证
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from langchain_core.messages import AIMessage, HumanMessage


class TestGraphRouting:
    """PG-01 ~ PG-04: LangGraph 图结构验证"""

    # PG-01: should_continue 有 tool_calls → "tools"
    def test_should_continue_with_tool_calls(self):
        from app.services.chat_graph import should_continue

        mock_msg = MagicMock()
        mock_msg.tool_calls = [{"name": "query_order", "args": {"orderId": "1"}}]
        state = {"messages": [mock_msg]}

        result = should_continue(state)
        assert result == "tools"

    # PG-02: should_continue 无 tool_calls → END
    def test_should_continue_without_tool_calls(self):
        from app.services.chat_graph import should_continue
        from langgraph.graph import END

        mock_msg = MagicMock()
        mock_msg.tool_calls = []
        state = {"messages": [mock_msg]}

        result = should_continue(state)
        assert result == END

    # PG-03: workflow 图包含 agent + tools 节点
    def test_workflow_has_required_nodes(self):
        from app.services.chat_graph import workflow
        # StateGraph 构造后可以检查节点
        assert "agent" in workflow.nodes
        assert "tools" in workflow.nodes

    # PG-04: save_chat_history 正常保存
    @pytest.mark.asyncio
    async def test_save_chat_history(self):
        from app.services.chat_graph import save_chat_history

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        await save_chat_history(mock_session, "session-1", "Hello", "World")

        assert mock_session.add.call_count == 2
        mock_session.commit.assert_awaited_once()
