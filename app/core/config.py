import os
from dotenv import load_dotenv
from functools import lru_cache

# Load environment variables from .env file (if still exists)
load_dotenv()

class Config:
    """Base configuration."""

    APP_ENV = os.getenv("APP_ENV", "development")

    # Server
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT") or 8181)

    # Nacos Bootstrap (Must be provided via Env or launch.json)
    NACOS_SERVER_ADDR = os.getenv("NACOS_SERVER_ADDR", "127.0.0.1:8848")
    NACOS_NAMESPACE = os.getenv("NACOS_NAMESPACE", "")
    NACOS_GROUP = os.getenv("NACOS_GROUP", "DEFAULT_GROUP")
    NACOS_USERNAME = os.getenv("NACOS_USERNAME", "")
    NACOS_PASSWORD = os.getenv("NACOS_PASSWORD", "")
    SERVICE_NAME = os.getenv("SERVICE_NAME", "python-agent")

    # MCP / Discovery
    MCP_BRAVE_PATH = os.getenv("MCP_BRAVE_PATH")
    NACOS_GATEWAY_SERVICE_NAME = os.getenv("NACOS_GATEWAY_SERVICE_NAME", "gateway")
    NACOS_JAVA_SERVICE_NAME = os.getenv("NACOS_JAVA_SERVICE_NAME", "ai-langchain4j")

    # Security
    JWT_SECRET = os.getenv("JWT_SECRET", "your-256-bit-secret-your-256-bit-secret")
    JWT_WHITELIST: list[str] = ["/health", "/docs", "/openapi.json", "/redoc"]

    # --- 以下配置建议全部通过 Nacos YAML 下发 ---
    # Database (Defaults provided to ensure bootstrap doesn't crash)
    PG_HOST = os.getenv("PG_HOST", "localhost")
    PG_PORT = int(os.getenv("PG_PORT") or 5432)
    PG_USER = os.getenv("PG_USER", "postgres")
    PG_PASSWORD = os.getenv("PG_PASSWORD", "postgres")
    PG_DB = os.getenv("PG_DB", "postgres")

    # 💡 关键点：将 URI 改为动态属性，解决 Nacos 配置热更新失效问题
    @property
    def DB_URI(self) -> str:
        return f"postgresql://{self.PG_USER}:{self.PG_PASSWORD}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DB}"

    @property
    def DB_ASYNC_URI(self) -> str:
        return f"postgresql+psycopg://{self.PG_USER}:{self.PG_PASSWORD}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DB}"

    # LLM
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "new-api")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "dummy")
    LLM_SKIP_SSL_VERIFY = os.getenv("LLM_SKIP_SSL_VERIFY", "true").lower() == "true"

    # KB
    KB_EMBEDDING_PROVIDER = os.getenv("KB_EMBEDDING_PROVIDER", "new-api")
    KB_EMBEDDING_MODEL = os.getenv("KB_EMBEDDING_MODEL", "text-embedding-3-small")
    KB_CHUNK_SIZE = int(os.getenv("KB_CHUNK_SIZE") or 500)
    KB_CHUNK_OVERLAP = int(os.getenv("KB_CHUNK_OVERLAP") or 50)
    KB_VECTOR_TABLE = os.getenv("KB_VECTOR_TABLE", "langchain_pg_embedding")
    KB_LLM_TEMPERATURE = float(os.getenv("KB_LLM_TEMPERATURE") or 0.7)

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

@lru_cache()
def get_settings():
    env = os.getenv("APP_ENV", "development")
    if env == "production":
        return ProductionConfig()
    return DevelopmentConfig()

settings = get_settings()
