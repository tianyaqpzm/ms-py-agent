from fastapi import APIRouter, Request
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from app.agent.factory import get_graph_runnable
from app.services.chat_graph import save_chat_history
from app.core.database import AsyncSessionLocal  # 🔥 从 database.py 导入 Session 工厂
from langchain_core.messages import HumanMessage
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


from typing import Optional

class ChatRequest(BaseModel):
    session_id: str
    message: str
    topic_id: Optional[str] = None


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/rest/dark/v1/agent/chat")
async def chat_endpoint(request: Request, body: ChatRequest):
    # 1. 拿到连接池
    lg_pool = request.app.state.lg_pool

    async def event_generator():
        # 🔥 2. 手动申请连接 (Context Manager)
        # 这样连接的生命周期就完全覆盖了整个流式响应过程 (Start -> End)
        async with lg_pool.connection() as conn:
            try:
                # 🔥🔥 3. 核弹级修复：再次强制禁用 Prepared Statements
                # 虽然 main.py 配了，但为了 100% 确保这个会话不报错，这里再设一次
                conn.prepare_threshold = None

                # 4. 把这个“干净”的连接传给 Graph
                graph = await get_graph_runnable(conn)

                input_message = HumanMessage(content=body.message)
                config = {"configurable": {"thread_id": body.session_id, "topic_id": body.topic_id}}
                final_response = ""

                # 5. 运行 Graph (使用当前的 conn)
                async for event in graph.astream_events(
                    {"messages": [input_message]}, config, version="v1"
                ):
                    kind = event["event"]
                    # ... 处理流逻辑 ...
                    if kind == "on_chain_end" and event["name"] == "agent":
                        output = event["data"]["output"]
                        # 兼容性处理，防止 output 为 None
                        if output and "messages" in output and output["messages"]:
                            final_response = output["messages"][-1].content
                            yield f"data: {json.dumps({'content': final_response})}\n\n"

                    # 还可以加个心跳，防止中间静默太久被防火墙切断
                    # yield ": keep-alive\n\n"

                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"Stream error: {e}", exc_info=True)
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

            # 离开 async with 时，连接会自动 rollback (如果出错) 并归还给 pool

        # --- 6. 历史记录保存 (连接归还后单独进行) ---
        # 此时 conn 已经还回去了，我们用 SQLAlchemy 的新连接存历史
        if final_response:
            async with AsyncSessionLocal() as session:
                try:
                    await save_chat_history(
                        session, body.session_id, body.message, final_response
                    )
                except Exception as e:
                    logger.error(f"History save failed: {e}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")
