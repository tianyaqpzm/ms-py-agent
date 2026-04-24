import logging
import yaml
from app.core.config import settings
from app.core.nacos import nacos_manager

logger = logging.getLogger(__name__)


class DynamicConfig:
    def __init__(self):
        # Default to environment variables
        self.llm_provider = settings.LLM_PROVIDER
        self.llm_base_url = settings.LLM_BASE_URL
        self.llm_model = settings.LLM_MODEL
        self.llm_api_key = settings.LLM_API_KEY

        # Nacos Config Info: Adopt Option 1 (Dynamic Data ID based on environment)
        # e.g., python-agent-development.yaml or python-agent-production.yaml
        self.data_id = f"{settings.SERVICE_NAME}-{settings.APP_ENV}.txt"
        self.group = settings.NACOS_GROUP

    def watch_config(self):
        """Start watching for configuration changes."""
        logger.info(f"🎧 Starting to watch config: {self.data_id}")

        # 1. Get initial config
        content = nacos_manager.get_config(self.data_id, self.group)
        if content:
            self._update_config(content)

        # 2. Add watcher
        nacos_manager.add_config_watcher(self.data_id, self.group, self._update_config)

    def _update_config(self, args):
        """Callback for Nacos config updates."""
        try:
            # args can be the content string directly or a dictionary depending on SDK version
            # Usually it's the content string in the callback
            content = args
            if isinstance(args, dict):
                content = args.get("content", "")

            if not content:
                logger.warning("⚠️ Received empty config update from Nacos")
                return

            logger.info("🔄 Received config update from Nacos")
            from io import StringIO
            from dotenv import dotenv_values

            # 解析 .env 格式的内容 (KEY=VALUE)
            config = dotenv_values(stream=StringIO(content))

            if config:
                # 直接从解析出的字典中读取配置 (通常建议与 .env/环境变量名保持一致)
                self.llm_provider = config.get("LLM_PROVIDER", self.llm_provider)
                self.llm_base_url = config.get("LLM_BASE_URL", self.llm_base_url)
                self.llm_model = config.get("LLM_MODEL", self.llm_model)
                self.llm_api_key = config.get("LLM_API_KEY", self.llm_api_key)

                logger.info(
                    f"✅ LLM Config Updated from .env: Provider={self.llm_provider}, Model={self.llm_model}, APIKey={'***' if self.llm_api_key != 'dummy' else 'dummy'}"
                )

        except Exception as e:
            logger.error(f"❌ Error updating config: {e}")


# Singleton instance
dynamic_config = DynamicConfig()
