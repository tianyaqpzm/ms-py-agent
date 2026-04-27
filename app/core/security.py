"""
JWT 身份校验依赖

逻辑与 ms-java-gateway JwtAuthenticationFilter 保持一致：
  1. 优先从 Cookie jwt_token 中读取 Token（浏览器场景）
  2. 兜底从 Authorization: Bearer <token> 中读取（API 调用场景）
  3. 白名单路径直接放行
  4. 校验使用与 ms-java-gateway 相同的 HMAC-SHA256 secret

使用方式（在路由函数中注入）:
    from app.core.security import get_current_user, CurrentUser

    @router.post("/some-endpoint")
    async def my_endpoint(body: MyRequest, user: CurrentUser = Depends(get_current_user)):
        # user.id / user.name / user.avatar 由 Gateway 注入的 Header 提供
        ...
"""

import jwt
import logging
from dataclasses import dataclass
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

logger = logging.getLogger(__name__)

# HTTPBearer 用于 Swagger UI 的 "Authorize" 按钮，auto_error=False 表示不强制要求（我们自己处理逻辑）
_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    """来自 JWT Payload 的用户信息（与 Gateway 解析的字段一致）"""
    id: str
    name: str
    avatar: str = ""
    raw_claims: dict = None  # 原始 claims，按需使用


def _extract_token(request: Request, credentials: HTTPAuthorizationCredentials | None) -> str | None:
    """
    按优先级提取 Token：
      1. Cookie jwt_token（浏览器场景，由 Gateway SSO 写入）
      2. Authorization: Bearer <token>（API 客户端 / ms-py-agent 内部调用）
    """
    # 优先读 Cookie
    cookie_token = request.cookies.get("jwt_token")
    if cookie_token:
        return cookie_token

    # 兜底读 Authorization Header
    if credentials and credentials.credentials:
        return credentials.credentials

    return None


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    """
    FastAPI Dependency：校验 JWT，返回当前用户信息。

    当 Gateway 正常工作时，X-User-* Header 已经由 Gateway 注入，可直接使用。
    此处额外做 Token 本地校验，作为纵深防御（Gateway 被绕过时的最后一道防线）。
    """
    token = _extract_token(request, credentials)

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token (Cookie jwt_token or Authorization header required)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # 使用与 ms-java-gateway 相同的 HMAC-SHA256 算法和 secret 解码
        claims = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid JWT token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 提取标准 claims（与 Gateway JwtAuthenticationFilter 解析字段对齐）
    user_id = claims.get("sub", "")
    username = claims.get("name") or claims.get("username", "")
    avatar = claims.get("picture") or claims.get("avatar", "")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject (sub) claim",
        )

    return CurrentUser(id=user_id, name=username, avatar=avatar, raw_claims=claims)
