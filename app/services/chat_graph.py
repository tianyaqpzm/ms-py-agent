from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.runnables.config import RunnableConfig
from app.core.database import ChatMessageModel
from app.core.llm_factory import LLMFactory
from app.core.dynamic_config import dynamic_config
from app.services.kb.retrieval import RetrievalService
import logging

logger = logging.getLogger(__name__)


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# Remove global LLM init
# llm = ...


# Define a simple graph
async def agent_node(state: ChatState, config: RunnableConfig):
    # Retrieve latest config
    provider = dynamic_config.llm_provider
    base_url = dynamic_config.llm_base_url
    model = dynamic_config.llm_model

    # Initialize LLM on the fly
    llm = LLMFactory.get_llm(provider=provider, base_url=base_url, model_name=model)

    messages = state["messages"]

    # RAG Integration Hook
    topic_id = config.get("configurable", {}).get("topic_id")
    if topic_id:
        try:
            ret_svc = RetrievalService()
            user_query = messages[-1].content if messages else ""
            if user_query:
                context_docs = await ret_svc.search(query=user_query, category=topic_id, top_k=5)
                if context_docs:
                    context_str = "\n---\n".join([d.get("content", "") for d in context_docs])
                    system_prompt = (
                        "You are a helpful assistant. Use the following context retrieved from the user's knowledge base to answer the query. "
                        "If the context is irrelevant, you may ignore it.\n\n"
                        f"Target Knowledge Base Context:\n{context_str}"
                    )
                    # Insert context as a SystemMessage (temporarily for the LLM call, not saved to state history unless returned)
                    messages = [SystemMessage(content=system_prompt)] + messages
        except Exception as e:
            logger.error(f"Failed to inject RAG context for topic={topic_id}: {e}")

    # Call the LLM
    response = await llm.ainvoke(messages)
    return {"messages": [response]}


workflow = StateGraph(ChatState)
workflow.add_node("agent", agent_node)
workflow.set_entry_point("agent")
workflow.add_edge("agent", END)


async def save_chat_history(session, session_id, human_msg, ai_msg):
    # session 是 SQLAlchemy 的 AsyncSession
    try:
        user_msg = ChatMessageModel(
            session_id=session_id, role="user", content=human_msg
        )
        ai_msg = ChatMessageModel(session_id=session_id, role="ai", content=ai_msg)

        session.add(user_msg)
        session.add(ai_msg)

        await session.commit()  # 提交事务
    except Exception as e:
        await session.rollback()
        raise e
