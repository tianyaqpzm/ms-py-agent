import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)


class LLMFactory:
    @staticmethod
    def get_llm(
        provider: str,
        base_url: str,
        model_name: str,
        api_key: str = "dummy",  # Gateway handles the real key
        temperature: float = 0.7,
    ) -> BaseChatModel:
        """
        Factory to create LLM instances based on provider.
        """
        logger.info(
            f"Initializing LLM: provider={provider}, model={model_name}, base_url={base_url}"
        )

        if provider.lower() == "gemini":
            # For Gemini via Gateway
            # We use transport="rest" to ensure it goes through standard HTTP/s
            # client_options={"api_endpoint": ...} overrides the default Google API host
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,  # Library requires a key, even if dummy
                transport="rest",
                client_options={"api_endpoint": base_url},
                temperature=temperature,
                convert_system_message_to_human=True,  # Gemini sometimes needs this
            )

        elif provider.lower() in ["openai", "new-api"]:
            # For OpenAI or New-API (OpenAI-compatible)
            import httpx
            from app.core.config import settings
            
            http_client = None
            if settings.LLM_SKIP_SSL_VERIFY:
                # 针对自签名证书，创建一个不验证 SSL 的 AsyncClient
                http_client = httpx.AsyncClient(verify=False)

            return ChatOpenAI(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                temperature=temperature,
                http_async_client=http_client,
            )

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    @staticmethod
    def get_embeddings(
        provider: str,
        model_name: str,
        base_url: str = None,
        api_key: str = "dummy",
    ):
        """
        Factory to create Embeddings instances based on provider.
        """
        if provider.lower() in ["new-api", "openai", "gemini"]:
            # Unify all remote API models (including Gemini, OpenAI, etc.) 
            # through 'new-api' using the standard OpenAI compatible interface.
            from langchain_openai import OpenAIEmbeddings
            import httpx
            from app.core.config import settings

            kwargs = {}
            if base_url:
                kwargs["base_url"] = base_url
            
            # 针对自签名证书，创建一个不验证 SSL 的 AsyncClient
            if settings.LLM_SKIP_SSL_VERIFY:
                kwargs["http_async_client"] = httpx.AsyncClient(verify=False)
            
            return OpenAIEmbeddings(
                model=model_name,
                api_key=api_key,
                **kwargs
            )
        # TODO: 本地 HuggingFace/sentence-transformers Embedding（依赖 torch）已移除，
        #       如需本地模型，请在此处重新实现并添加相应的依赖。
        else:
            raise ValueError(f"Unsupported Embedding provider: {provider}")
